import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="Who Stopped Trading?", page_icon="🕵️‍♂️", layout="wide")

st.markdown("<h1 style='text-align: center; color: #1f77b4;'>🕵️‍♂️ Who Stopped Trading?</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #666; font-size: 18px; margin-bottom: 5px;'>수입/수출 양방향의 <b>이탈 및 환승(공급선 이동)</b>을 독립적으로 추적하는 듀얼 레이더 🚨</p>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888; font-size: 14px;'>📊 <b>데이터 단위 기준:</b> 중량(KG) &nbsp;|&nbsp; 금액(USD) &nbsp;|&nbsp; 단가(USD/KG)</p>", unsafe_allow_html=True)
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
        st.header("⏱️ 기준일 설정")
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
        st.header("📅 롤링 기간 설정")
        period_option = st.selectbox(
            "비교 기간 선택 (최근 vs 직전)",
            ["최근 1개월", "최근 3개월", "최근 6개월", "최근 1년", "최근 3년", "직접 입력"]
        )

        st.markdown("---")
        with st.expander("📖 활용 설명 (컬럼 안내)", expanded=False):
            st.markdown("""
            **[공통 지표]**
            - **최근/직전 수입량**: 필터에서 설정한 비교 기간 동안의 '1:1 거래' 기준 수입 중량 (KG)
            - **과거 평균 수량**: 전체 데이터 기간을 기준으로 한 1:1 거래의 통상적인 평균 수입 중량
            
            **[수입업체 표 - 💡공급선 변경 추적]**
            - **추출 기준**: '전체 수입량'이 과거 대비 감소한 한국 수입사만 독자적으로 색출합니다.
            - **세부 추이**: 각 수입사의 세부 거래선별로 🔼물량 확대(대체/환승), 🆕신규 거래, 🔽물량 축소, 🛑거래 중단 여부를 보여줍니다.
            
            **[수출사 표 - 💡한국 시장 이탈 추적]**
            - **추출 기준**: 수입사 이탈 여부와 관계없이, 한국으로 보내는 '전체 수출량' 자체가 감소한 해외 수출사만 독자적으로 색출합니다.
            - **세부 추이**: 해당 수출사가 기존 한국 수입사와의 거래가 축소/중단(🔽/🛑)되었는지, 혹은 다른 한국 수입사로 공급을 확대(🔼/🆕)하여 파이프라인을 전환했는지 파악합니다.
            """)

    # 기본 필터 적용
    filtered_df = df.copy()
    if hs_codes: filtered_df = filtered_df[filtered_df['HS-CODE'].isin(hs_codes)]
    if categories: filtered_df = filtered_df[filtered_df['Category'].isin(categories)]
    if origin_countries: filtered_df = filtered_df[filtered_df['Origin Country'].isin(origin_countries)]

    # --- 3. 기간 계산 ---
    curr_end = today
    if period_option == "최근 1개월":
        curr_start = curr_end - relativedelta(months=1) + relativedelta(days=1)
        past_end = curr_start - relativedelta(days=1)
        past_start = past_end - relativedelta(months=1) + relativedelta(days=1)
    elif period_option == "최근 3개월":
        curr_start = curr_end - relativedelta(months=3) + relativedelta(days=1)
        past_end = curr_start - relativedelta(days=1)
        past_start = past_end - relativedelta(months=3) + relativedelta(days=1)
    elif period_option == "최근 6개월":
        curr_start = curr_end - relativedelta(months=6) + relativedelta(days=1)
        past_end = curr_start - relativedelta(days=1)
        past_start = past_end - relativedelta(months=6) + relativedelta(days=1)
    elif period_option == "최근 1년":
        curr_start = curr_end - relativedelta(years=1) + relativedelta(days=1)
        past_end = curr_start - relativedelta(days=1)
        past_start = past_end - relativedelta(years=1) + relativedelta(days=1)
    elif period_option == "최근 3년":
        curr_start = curr_end - relativedelta(years=3) + relativedelta(days=1)
        past_end = curr_start - relativedelta(days=1)
        past_start = past_end - relativedelta(years=3) + relativedelta(days=1)
    elif period_option == "직접 입력":
        curr_dates = st.sidebar.date_input("최근 기간 (Current)", [today - relativedelta(months=1), today])
        past_dates = st.sidebar.date_input("과거 비교 기간 (Past)", [today - relativedelta(months=2), today - relativedelta(months=1)])
        if len(curr_dates) == 2 and len(past_dates) == 2:
            curr_start, curr_end = curr_dates[0], curr_dates[1]
            past_start, past_end = past_dates[0], past_dates[1]

    curr_start, curr_end = pd.to_datetime(curr_start), pd.to_datetime(curr_end)
    past_start, past_end = pd.to_datetime(past_start), pd.to_datetime(past_end)

    st.markdown("#### ⏳ 분석 기준 기간")
    col1, col2 = st.columns(2)
    col1.info(f"**최근 기간 (Current):** {curr_start.strftime('%Y-%m-%d')} ~ {curr_end.strftime('%Y-%m-%d')}")
    col2.info(f"**직전 비교 기간 (Past):** {past_start.strftime('%Y-%m-%d')} ~ {past_end.strftime('%Y-%m-%d')}")

    # --- 데이터 분리 ---
    curr_df = filtered_df[(filtered_df['Date'] >= curr_start) & (filtered_df['Date'] <= curr_end)]
    past_df = filtered_df[(filtered_df['Date'] >= past_start) & (filtered_df['Date'] <= past_end)]

    # =========================================================================
    # 🌟 수입사 레이더 (수입사 전체 총량 기준 독립 필터링)
    # =========================================================================
    imp_curr_vol = curr_df.groupby('Raw Importer Name')['Volume'].sum().reset_index().rename(columns={'Volume': 'Current Volume'})
    imp_past_vol = past_df.groupby('Raw Importer Name')['Volume'].sum().reset_index().rename(columns={'Volume': 'Past Volume'})
    imp_result_df = pd.merge(imp_past_vol, imp_curr_vol, on='Raw Importer Name', how='outer').fillna(0)
    
    imp_result_df['Volume Decrease'] = imp_result_df['Past Volume'] - imp_result_df['Current Volume']
    imp_result_df = imp_result_df[imp_result_df['Volume Decrease'] > 0] 
    imp_result_df['Is Stopped'] = imp_result_df['Current Volume'] == 0

    if not imp_result_df.empty:
        target_importers = imp_result_df['Raw Importer Name'].tolist()
        
        # KPI & 상단 차트
        st.markdown("<br>", unsafe_allow_html=True)
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric(label="총 수입 감소/중단 업체 수", value=f"{len(imp_result_df)} 개사")
        kpi2.metric(label="완전 거래 중단 업체 수", value=f"{len(imp_result_df[imp_result_df['Is Stopped']])} 개사", delta="-100%", delta_color="inverse")
        kpi3.metric(label="총 증발된 수입량 (KG)", value=f"{imp_result_df['Volume Decrease'].sum():,.2f}")
        st.markdown("---")

        # 🌟 Plotly 적용: Top 10 바 차트 (드래그 박스 줌, 호버, 정렬 완벽 지원) 🌟
        st.markdown("#### 📊 Top 10 수입 물량 급감 업체")
        chart_df = imp_result_df.sort_values(by='Volume Decrease', ascending=False).head(10)
        
        fig_bar = px.bar(
            chart_df, 
            x='Raw Importer Name', 
            y='Volume Decrease',
            labels={'Raw Importer Name': '수입 업체명', 'Volume Decrease': '총 감소량 (KG)'},
            color_discrete_sequence=['#ff4b4b']
        )
        fig_bar.update_layout(
            xaxis={'categoryorder':'total descending'}, # 완벽한 내림차순 계단식 정렬
            margin=dict(l=0, r=0, t=20, b=0),
            height=350,
            dragmode='zoom' # 드래그 시 박스 형태로 줌인
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # 수입사 표
        st.markdown("---")
        st.markdown("#### 📉 수입업체 (Importer) 관점 : 이탈 현황")

        imp_detail_df = filtered_df[filtered_df['Raw Importer Name'].isin(target_importers)].copy()
        imp_detail_df['Export Country'] = imp_detail_df['Export Country'].fillna('Unknown')
        imp_detail_df['Exporter'] = imp_detail_df['Exporter'].fillna('Unknown')
        imp_detail_df['Exporter Line'] = "[" + imp_detail_df['Export Country'] + "] " + imp_detail_df['Exporter']

        imp_curr_detail = imp_detail_df[(imp_detail_df['Date'] >= curr_start) & (imp_detail_df['Date'] <= curr_end)].groupby(['Raw Importer Name', 'Exporter Line'])['Volume'].sum().reset_index(name='Current Volume')
        imp_past_detail = imp_detail_df[(imp_detail_df['Date'] >= past_start) & (imp_detail_df['Date'] <= past_end)].groupby(['Raw Importer Name', 'Exporter Line'])['Volume'].sum().reset_index(name='Past Volume')
        
        imp_merged = pd.merge(imp_past_detail, imp_curr_detail, on=['Raw Importer Name', 'Exporter Line'], how='outer').fillna(0)
        imp_merged['Volume Change'] = imp_merged['Current Volume'] - imp_merged['Past Volume']
        
        def get_line_trend(row):
            if row['Past Volume'] == 0 and row['Current Volume'] > 0:
                return "🆕 신규 거래"
            elif row['Current Volume'] == 0 and row['Past Volume'] > 0:
                return "🛑 거래 중단"
            elif row['Volume Change'] > 0:
                return "🔼 물량 확대"
            elif row['Volume Change'] < 0:
                return "🔽 물량 축소"
            else:
                return "➖ 유지 (변동 없음)"
                
        imp_merged['세부 추이'] = imp_merged.apply(get_line_trend, axis=1)

        imp_period_avg = imp_detail_df.groupby(['Raw Importer Name', 'Exporter Line', imp_detail_df['Date'].dt.to_period('Y')])['Volume'].sum().reset_index()
        imp_avg_vol = imp_period_avg.groupby(['Raw Importer Name', 'Exporter Line'])['Volume'].mean().reset_index(name='Avg Volume')
        
        imp_price_stats = imp_detail_df.groupby(['Raw Importer Name', 'Exporter Line']).apply(
            lambda x: pd.Series({
                'Arithmetic Avg Price': x['Unit Price'].mean(),
                'Weighted Avg Price': x['Value'].sum() / x['Volume'].sum() if x['Volume'].sum() > 0 else 0
            })
        ).reset_index()

        final_imp_df = imp_merged.merge(imp_avg_vol, on=['Raw Importer Name', 'Exporter Line'], how='left') \
                                 .merge(imp_price_stats, on=['Raw Importer Name', 'Exporter Line'], how='left')

        num_cols_imp = ['Current Volume', 'Past Volume', 'Volume Change', 'Avg Volume', 'Arithmetic Avg Price', 'Weighted Avg Price']
        final_imp_df[num_cols_imp] = final_imp_df[num_cols_imp].round(2)

        imp_total_decrease = final_imp_df.groupby('Raw Importer Name')['Volume Change'].sum().reset_index(name='Total Decrease')
        final_imp_df = final_imp_df.merge(imp_total_decrease, on='Raw Importer Name')
        
        final_imp_df = final_imp_df.sort_values(by=['Total Decrease', 'Raw Importer Name', 'Volume Change'], ascending=[True, True, False])
        
        final_imp_df = final_imp_df[['Raw Importer Name', '세부 추이', 'Exporter Line', 'Past Volume', 'Current Volume', 'Volume Change', 'Avg Volume', 'Arithmetic Avg Price', 'Weighted Avg Price']]
        final_imp_df.rename(columns={
            'Raw Importer Name': '수입업체명',
            'Exporter Line': '거래 수출업체',
            'Past Volume': '직전 수입량',
            'Current Volume': '최근 수입량',
            'Volume Change': '거래량 증감 (+/-)',
            'Avg Volume': '과거 평균 수량',
            'Arithmetic Avg Price': '산술단가 ($)',
            'Weighted Avg Price': '가중단가 ($)'
        }, inplace=True)

        final_imp_df.set_index(['수입업체명'], inplace=True)
        st.dataframe(final_imp_df, use_container_width=True)

    else:
        st.success("조건에 맞는 수입 감소/중단 업체가 없습니다. 대단하네요! 🎉")


    # =========================================================================
    # 🌟 수출사 레이더
    # =========================================================================
    st.markdown("---")
    st.markdown("#### 🔄 수출사(Exporter) 관점 : 한국 시장 이탈 및 환승 현황")

    exp_curr_total = curr_df.groupby('Exporter')['Volume'].sum().reset_index(name='Current Total')
    exp_past_total = past_df.groupby('Exporter')['Volume'].sum().reset_index(name='Past Total')
    exp_radar = pd.merge(exp_past_total, exp_curr_total, on='Exporter', how='outer').fillna(0)
    
    exp_radar['Total Decrease'] = exp_radar['Past Total'] - exp_radar['Current Total']
    exp_radar = exp_radar[exp_radar['Total Decrease'] > 0] 

    if not exp_radar.empty:
        target_exporters = exp_radar['Exporter'].tolist()
        exp_detail_df = filtered_df[filtered_df['Exporter'].isin(target_exporters)].copy()
        
        exp_curr_detail = exp_detail_df[(exp_detail_df['Date'] >= curr_start) & (exp_detail_df['Date'] <= curr_end)].groupby(['Exporter', 'Raw Importer Name'])['Volume'].sum().reset_index(name='Current Volume')
        exp_past_detail = exp_detail_df[(exp_detail_df['Date'] >= past_start) & (exp_detail_df['Date'] <= past_end)].groupby(['Exporter', 'Raw Importer Name'])['Volume'].sum().reset_index(name='Past Volume')
        
        exp_merged = pd.merge(exp_past_detail, exp_curr_detail, on=['Exporter', 'Raw Importer Name'], how='outer').fillna(0)
        exp_merged['Volume Change'] = exp_merged['Current Volume'] - exp_merged['Past Volume']
        
        def get_exp_trend(row):
            if row['Past Volume'] == 0 and row['Current Volume'] > 0:
                return "🆕 신규 거래"
            elif row['Current Volume'] == 0 and row['Past Volume'] > 0:
                return "🛑 거래 중단"
            elif row['Volume Change'] > 0:
                return "🔼 물량 확대"
            elif row['Volume Change'] < 0:
                return "🔽 물량 축소"
            else:
                return "➖ 유지 (변동 없음)"
                
        exp_merged['Trend'] = exp_merged.apply(get_exp_trend, axis=1)

        final_exp_df = exp_merged.copy()
        num_cols_exp = ['Past Volume', 'Current Volume', 'Volume Change']
        final_exp_df[num_cols_exp] = final_exp_df[num_cols_exp].round(2)

        exp_total_decrease = final_exp_df.groupby('Exporter')['Volume Change'].sum().reset_index(name='Total Decrease')
        final_exp_df = final_exp_df.merge(exp_total_decrease, on='Exporter')
        
        final_exp_df = final_exp_df.sort_values(by=['Total Decrease', 'Exporter', 'Volume Change'], ascending=[True, True, False])

        final_exp_df = final_exp_df[['Exporter', 'Trend', 'Raw Importer Name', 'Past Volume', 'Current Volume', 'Volume Change']]
        final_exp_df.rename(columns={
            'Exporter': '해외 수출사',
            'Trend': '세부 추이',
            'Raw Importer Name': '한국 내 수입사',
            'Past Volume': '직전 수입량',
            'Current Volume': '최근 수입량',
            'Volume Change': '거래량 증감 (+/-)'
        }, inplace=True)

        final_exp_df.set_index(['해외 수출사'], inplace=True)

        st.dataframe(final_exp_df, use_container_width=True)
    else:
        st.success("한국으로의 전체 수출량이 감소한 해외 수출사가 없습니다!")

    # =========================================================================
    # --- 7. 1:1 장기 거래 추이 시각화 ---
    # =========================================================================
    st.markdown("---")
    st.markdown("#### 📈 특정 수입사-수출사 1:1 장기 거래 추이")
    
    col_imp, col_exp = st.columns(2)
    all_importers = sorted(filtered_df['Raw Importer Name'].dropna().unique().tolist())
    selected_imp = col_imp.selectbox("🏢 추이를 확인할 '수입사(Importer)' 선택", options=["선택 안함"] + all_importers)
    
    if selected_imp != "선택 안함":
        available_exporters = sorted(filtered_df[filtered_df['Raw Importer Name'] == selected_imp]['Exporter'].dropna().unique().tolist())
    else:
        available_exporters = sorted(filtered_df['Exporter'].dropna().unique().tolist())
        
    selected_exp = col_exp.selectbox("🚢 추이를 확인할 '수출사(Exporter)' 선택", options=["선택 안함"] + available_exporters)
    
    if selected_imp != "선택 안함" and selected_exp != "선택 안함":
        trend_df = filtered_df[(filtered_df['Raw Importer Name'] == selected_imp) & (filtered_df['Exporter'] == selected_exp)].copy()
        
        if not trend_df.empty:
            trend_df['Month'] = trend_df['Date'].dt.to_period('M').dt.to_timestamp()
            monthly_trend = trend_df.groupby('Month')['Volume'].sum().reset_index()
            
            total_1to1_volume = trend_df['Volume'].sum()
            avg_per_transaction = trend_df['Volume'].mean()
            
            m1, m2, m3 = st.columns([1, 1, 2])
            m1.metric("📦 1:1 총 누적 거래량", f"{total_1to1_volume:,.2f} KG")
            m2.metric("🧾 1건당 평균 거래량", f"{avg_per_transaction:,.2f} KG")
            
            # 🌟 Plotly 적용: 라인 차트 (더블클릭 리셋, 영역 드래그 줌인) 🌟
            fig_line = px.line(
                monthly_trend, 
                x='Month', 
                y='Volume',
                markers=True,
                labels={'Month': '연/월', 'Volume': '수입량 (KG)'}
            )
            fig_line.update_traces(line_color='#1f77b4', line_width=3, marker_size=8)
            fig_line.update_layout(
                margin=dict(l=0, r=0, t=20, b=0),
                height=350,
                dragmode='zoom' # 드래그 시 박스 형태로 특정 기간 줌인
            )
            st.plotly_chart(fig_line, use_container_width=True)
            
        else:
            st.info("ℹ️ 해당 수입사와 수출사 간의 거래 기록이 없습니다.")
else:
    st.info("👈 좌측 사이드바에서 분석할 데이터를 업로드 해주세요.")
