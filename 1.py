import streamlit as st
import pandas as pd
import numpy as np

def incsv(uploaded_file):
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    return df                       

def averagedailysales(df, p_idx, q_idx, d_idx):
    p_col = df.columns[p_idx]
    q_col = df.columns[q_idx]
    d_col = df.columns[d_idx]

    df[d_col] = pd.to_datetime(df[d_col])
    total_days = (df[d_col].max() - df[d_col].min()).days
    if total_days <= 0: total_days = 1

    velocity = df.groupby(p_col)[q_col].sum().reset_index()
    velocity['Daily_Sales'] = velocity[q_col] / total_days
    return velocity, p_col

def leadtime(df_merge, supplier_days):
    df_merge['final_lead'] = df_merge['Daily_Sales'] * df_merge[supplier_days]
    return df_merge

def safetystock(df_merge):
    df_merge['Safety_stock'] = df_merge['final_lead'] * 0.5
    return df_merge

def Reorderpoint(df_merge):
    df_merge['finalized'] = df_merge['final_lead'] + df_merge['Safety_stock']
    return df_merge

def checker(df_merge, stock_col):
    df_merge['status'] = np.where(df_merge[stock_col] <= df_merge['finalized'], 'ORDER NOW', 'STOCK OK')
    return df_merge

def days_left(df_merge, stock_col):
    df_merge['Days_left'] = df_merge[stock_col] / df_merge['Daily_Sales'].replace(0, np.nan)
    return df_merge

def inventoryhealth(df_merge):
    df_merge['inventory'] = np.where(df_merge['Days_left'] > 90, 'Overstock', 'Healthy')
    return df_merge

def main():
    st.set_page_config(layout="wide")
    st.title("Inventory Health & Reorder Planner")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Sales Data Configuration")
        sales_file = st.file_uploader("Upload Sales File", type=['csv', 'xlsx'])
        if sales_file:
            sales_df = incsv(sales_file)
            cols = sales_df.columns.tolist()
            p_idx = st.selectbox("Product ID Column", range(len(cols)), format_func=lambda x: cols[x])
            q_idx = st.selectbox("Quantity Column", range(len(cols)), format_func=lambda x: cols[x])
            d_idx = st.selectbox("Date Column", range(len(cols)), format_func=lambda x: cols[x])

    with col2:
        st.subheader("Stock Data Configuration")
        stock_file = st.file_uploader("Upload Stock File", type=['csv', 'xlsx'])
        if stock_file:
            stock_df = incsv(stock_file)
            s_cols = stock_df.columns.tolist()
            s_p_idx = st.selectbox("Stock Product ID", range(len(s_cols)), format_func=lambda x: s_cols[x])
            days_idx = st.selectbox("Supplier Days Column", range(len(s_cols)), format_func=lambda x: s_cols[x])
            stock_idx = st.selectbox("Current Stock Column", range(len(s_cols)), format_func=lambda x: s_cols[x])

    if sales_file and stock_file:
        if st.button("Generate Inventory Plan"):
            velocity_df, p_col_name = averagedailysales(sales_df, p_idx, q_idx, d_idx)
            
            s_p_name = stock_df.columns[s_p_idx]
            s_days = stock_df.columns[days_idx]
            s_stock = stock_df.columns[stock_idx]

            df_merge = pd.merge(velocity_df, stock_df[[s_p_name, s_days, s_stock]], 
                                left_on=p_col_name, right_on=s_p_name, how='inner')
            
            df_merge = leadtime(df_merge, s_days)
            df_merge = safetystock(df_merge)
            df_merge = Reorderpoint(df_merge)
            df_merge = checker(df_merge, s_stock)
            df_merge = days_left(df_merge, s_stock)
            df_merge = inventoryhealth(df_merge)

            st.divider()
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Products", len(df_merge))
            m2.metric("Items to Reorder", len(df_merge[df_merge['status'] == 'ORDER NOW']))
            m3.metric("Overstock Items", len(df_merge[df_merge['inventory'] == 'Overstock']))

            st.dataframe(df_merge, use_container_width=True)
            
            csv = df_merge.to_csv(index=False).encode('utf-8')
            st.download_button("Download Report", data=csv, file_name="inventory_report.csv", mime="text/csv")

if __name__ == "__main__":
    main()