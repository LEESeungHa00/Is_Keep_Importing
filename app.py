import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="Still Importing?", page_icon="📉", layout="wide")
st.markdown("<h1 style='text-align: center; color: #1f77b4;'>📉 수입 감소 및 중단 업체 분석 대시보드</h1>", unsafe_allow_html=True)
st.markdown("---")

# --- 2. 데이터 업로드 ---
uploaded_file = st.sidebar.file_uploader("📂 데이터 파일 업로드 (CSV/Excel)", type=['csv', 'xlsx'])

if uploaded_file:
    @st.cache_data
    def load_data(file):
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        df['Date'] = pd.to_datetime(df['Date'])
        return df

    df = load_data(uploaded_file)
    
    with st.sidebar:
        st.header("⏱️ 기준일 설정 (Reference Date)")
        ref_date_option = st.radio(
            "기간을 계산할 '오늘'의 기준을 선택하세요",
            ["데이터 최신 날짜 기준 (권장)", "서버 현재 시간 (오늘)"]
        )
        
        if ref_date_option == "데이터 최신 날짜 기준 (권장)":
            today = df['Date'].max().date()
        else:
            today = datetime.now().date()

        st.markdown("---")
        st.header("🔍 상세 필터 설정")
        def multiselect_filter(label, column):
            options = df[column].dropna().unique().tolist()
            return st.multiselect(label, options, default=[])

        hs_codes = multiselect_filter("HS-CODE", "HS-CODE")
        categories = multiselect_filter("Category", "Category")
        origin_countries = multiselect_filter("Origin Country", "Origin Country")
        
        st.markdown("---")
        st.header("📅 기간 설정")
        period_option = st.selectbox(
            "비교 기간 선택",
            ["전월 대비", "전분기 대비", "전반기 대비", "전년대비", "전3년 대비", "전5년 대비", "직접 입력"]
        )

    # 기본 필터 적용
    filtered_df = df.copy()
    if hs_codes: filtered_df = filtered_df[filtered_df['HS-CODE'].isin(hs_codes)]
    if categories: filtered_df = filtered_df[filtered_df['Category'].isin(categories)]
    if origin_countries: filtered_df = filtered_df[filtered_df['Origin Country'].isin(origin_countries)]

    # 기간 구하는 로직
    curr_start, curr_end = today, today
    past_start, past_end = today, today
    period_type = "Year"

    if period_option == "전월 대비":
        curr_start = today.replace(day=1)
        past_end = curr_start - relativedelta(days=1)
        past_start = past_end.replace(day=1)
        period_type = "Month"
    elif period_option == "전분기 대비":
        curr_quarter_start_month = 3 * ((today.month - 1) // 3) + 1
        curr_start = today.replace(month=curr_quarter_start_month, day=1)
        past_end = curr_start - relativedelta(days=1)
        past_start = past_end.replace(month=3 * ((past_end.month - 1) // 3) + 1, day=1)
        period_type = "Quarter"
    elif period_option == "전반기 대비":
        curr_half_start_month = 1 if today.month <= 6 else 7
        curr_start = today.replace(month=curr_half_start_month, day=1)
        past_end = curr_start - relativedelta(days=1)
        past_start = past_end.replace(month=1 if past_end.month <= 6 else 7, day=1)
        period_type = "HalfYear"
    elif period_option in ["전년대비", "전3년 대비", "전5년 대비"]:
        years = 1 if period_option == "전년대비" else (3 if period_option == "전3년 대비" else 5)
        curr_start = today.replace(month=1, day=1)
        past_start = curr_start - relativedelta(years=years)
        past_end = past_start.replace(month=12, day=31)
    elif period_option == "직접 입력":
        curr_dates = st.sidebar.date_input("최근 기간 (Current)", [today - relativedelta(months=1), today])
        past_dates = st.sidebar.date_input("과거 기간 (Past)", [today - relativedelta(months=2), today - relativedelta(months=1)])
        if len(curr_dates) == 2 and len(past_dates) == 2:
            curr_start, curr_end = curr_dates[0], curr_dates[1]
            past_start, past_end = past_dates[0], past_dates[1]
        period_type = "Custom"

    curr_start, curr_end = pd.to_datetime(curr_start), pd.to_datetime(curr_end)
    past_start, past_end = pd.to_datetime(past_start), pd.to_datetime(past_end)
    curr_days = (curr_end - curr_start).days + 1
    past_days = (past_end - past_start).days + 1

    # 상단 기간 요약 박스
    st.markdown("#### ⏳ 분석 기준 기간")
    col1, col2 = st.columns(2)
    col1.info(f"**최근 기간 (Current):** {curr_start.strftime('%Y-%m-%d')} ~ {curr_end.strftime('%Y-%m-%d')} ({curr_days}일)")
    col2.info(f"**과거 기간 (Past):** {past_start.strftime('%Y-%m-%d')} ~ {past_end.strftime('%Y-%m-%d')} ({past_days}일)")

    if curr_days != past_days:
        st.warning(f"⚠️ **주의:** 역년/월 산정 기준으로 인해 두 기간의 일수({curr_days}일 vs {past_days}일)가 다릅니다. 비교 시 수치가 왜곡될 수 있습니다.")

    # --- 5. 데이터 연산 ---
    curr_df = filtered_df[(filtered_df['Date'] >= curr_start) & (filtered_df['Date'] <= curr_end)]
    past_df = filtered_df[(filtered_df['Date'] >= past_start) & (filtered_df['Date'] <= past_end)]

    curr_vol = curr_df.groupby('Raw Importer Name')['Volume'].sum().reset_index().rename(columns={'Volume': 'Current Volume'})
    past_vol = past_df.groupby('Raw Importer Name')['Volume'].sum().reset_index().rename(columns={'Volume': 'Past Volume'})
    result_df = pd.merge(past_vol, curr_vol, on='Raw Importer Name', how='outer').fillna(0)
    
    result_df['Volume Decrease'] = result_df['Past Volume'] - result_df['Current Volume']
    result_df = result_df[result_df['Volume Decrease'] > 0]
    result_df['Is Stopped'] = result_df['Current Volume'] == 0

    if not result_df.empty:
        target_importers = result_df['Raw Importer Name'].tolist()
        stats_df = filtered_df[filtered_df['Raw Importer Name'].isin(target_importers)].copy()
        
        if period_type == "Month":
            stats_df['Period_Key'] = stats_df['Date'].dt.to_period('M')
        elif period_type == "Quarter":
            stats_df['Period_Key'] = stats_df['Date'].dt.to_period('Q')
        elif period_type == "HalfYear":
            stats_df['Period_Key'] = stats_df['Date'].dt.year.astype(str) + "H" + np.where(stats_df['Date'].dt.month <= 6, '1', '2')
        else:
            stats_df['Period_Key'] = stats_df['Date'].dt.to_period('Y')
        
        avg_vol = stats_df.groupby(['Raw Importer Name', 'Period_Key'])['Volume'].sum().reset_index()
        avg_vol = avg_vol.groupby('Raw Importer Name')['Volume'].mean().reset_index().rename(columns={'Volume': 'Avg Volume'})

        price_stats = stats_df.groupby('Raw Importer Name').apply(
            lambda x: pd.Series({
                'Arithmetic Avg Price': x['Unit Price'].mean(),
                'Weighted Avg Price': x['Value'].sum() / x['Volume'].sum() if x['Volume'].sum() > 0 else 0
            })
        ).reset_index()

        def format_exporters(group):
            group = group.copy()
            group['Export Country'] = group['Export Country'].fillna('Unknown Country')
            group['Exporter'] = group['Exporter'].fillna('Unknown Exporter')
            
            grouped = group.groupby(['Export Country', 'Exporter'])['Volume'].sum().reset_index()
            country_totals = grouped.groupby('Export Country')['Volume'].sum().reset_index().rename(columns={'Volume': 'Country Total'})
            merged = pd.merge(grouped, country_totals, on='Export Country')
            merged = merged.sort_values(by=['Country Total', 'Volume'], ascending=[False, False])
            
            lines = []
            curr_country = ""
            for _, row in merged.iterrows():
                if row['Export Country'] != curr_country:
                    curr_country = row['Export Country']
                    lines.append(f"[{curr_country}]")
                # 수출업체 수입량도 소수점 2자리까지만 표출 (필요에 따라 .0f로 유지 가능하지만 통일감을 위해 변경)
                lines.append(f"  - {row['Exporter']} ({row['Volume']:,.2f})")
            return "\n".join(lines)

        exporter_info = stats_df.groupby('Raw Importer Name').apply(format_exporters).reset_index(name='Existing Trade Line')

        final_df = result_df.merge(avg_vol, on='Raw Importer Name', how='left') \
                            .merge(price_stats, on='Raw Importer Name', how='left') \
                            .merge(exporter_info, on='Raw Importer Name', how='left')

        final_df = final_df.sort_values(by=['Is Stopped', 'Volume Decrease'], ascending=[False, False])
        final_df['Status'] = final_df['Is Stopped'].apply(lambda x: "🛑 단절" if x else "📉 감소")
        
        # 🌟 데이터프레임 내 모든 숫자 데이터를 강제로 소수점 2자리에서 반올림 처리
        numeric_cols = ['Current Volume', 'Past Volume', 'Volume Decrease', 'Avg Volume', 'Arithmetic Avg Price', 'Weighted Avg Price']
        final_df[numeric_cols] = final_df[numeric_cols].round(2)
        
        # --- 시각화 영역 ---
        st.markdown("<br>", unsafe_allow_html=True)
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric(label="총 수입 감소 업체 수", value=f"{len(final_df)} 개사")
        kpi2.metric(label="완전 거래 단절 업체 수", value=f"{len(final_df[final_df['Is Stopped']])} 개사", delta="-100%", delta_color="inverse")
        # KPI 감소량 소수점 2자리 표기
        kpi3.metric(label="총 감소 수입량 (KG)", value=f"{final_df['Volume Decrease'].sum():,.2f}")
        st.markdown("---")

        st.markdown("#### 📊 Top 10 수입 물량 급감 업체 (단절 여부 무관)")
        chart_df = final_df.sort_values(by='Volume Decrease', ascending=False).head(10)
        chart_data = chart_df[['Raw Importer Name', 'Volume Decrease']].set_index('Raw Importer Name')
        st.bar_chart(chart_data, color="#ff4b4b")

        st.markdown("#### 📋 상세 리스트")
        display_df = final_df[['Status', 'Raw Importer Name', 'Current Volume', 'Past Volume', 'Volume Decrease', 
                               'Avg Volume', 'Arithmetic Avg Price', 'Weighted Avg Price', 'Existing Trade Line']]
        
        # 🌟 UI 설정: 모든 표출 형식(format)을 소수점 2자리(%.2f)로 제한
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.TextColumn("상태", width="small"),
                "Raw Importer Name": st.column_config.TextColumn("업체명", width="medium"),
                "Current Volume": st.column_config.NumberColumn("최근 수입량", format="%,.2f"),
                "Past Volume": st.column_config.NumberColumn("과거 수입량", format="%,.2f"),
                "Volume Decrease": st.column_config.NumberColumn("감소량 ▼", format="%,.2f"),
                "Avg Volume": st.column_config.NumberColumn("평균 수입량", format="%,.2f"),
                "Arithmetic Avg Price": st.column_config.NumberColumn("산술평균단가", format="$%,.2f"),
                "Weighted Avg Price": st.column_config.NumberColumn("가중평균단가", format="$%,.2f"),
                "Existing Trade Line": st.column_config.TextColumn("기존 거래국/수출업체", width="large")
            }
        )
    else:
        st.success("조건에 맞는 수입 감소/단절 업체가 없습니다. 선택하신 기간의 데이터를 다시 확인해 주세요! 🎉")
else:
    st.info("👈 좌측 사이드바에서 분석할 Tridge 데이터를 업로드 해주세요.")
