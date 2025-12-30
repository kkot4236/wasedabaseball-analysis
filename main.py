import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import os

# ==================================================
# 0. パスワード保護機能
# ==================================================
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    def password_entered():
        if st.session_state["password"] == "waseda123": # 設定したパスワード
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    st.text_input("パスワードを入力してください", type="password", on_change=password_entered, key="password")
    if st.session_state.get("password_correct") == False:
        st.error("😕 パスワードが違います。")
    st.info("※部外者のアクセスを防ぐため、チーム共通のパスワードが必要です。")
    return False

# パスワードチェック実行
if check_password():

    # ==================================================
    # 1. 基本設定
    # ==================================================
    PITCH_LIST = ['Fastball', 'Slider', 'Cutter', 'Curveball', 'Splitter', 'ChangeUp', 'Sinker', 'TwoSeamFastBall']
    PITCH_CONFIG = {
        'Fastball': {'color': '#FF4B4B', 'marker': 'o'}, 'Slider': {'color': '#1E90FF', 'marker': '<'}, 
        'Cutter': {'color': '#FF1493', 'marker': 's'}, 'Curveball': {'color': '#32CD32', 'marker': '^'}, 
        'Splitter': {'color': '#40E0D0', 'marker': 's'}, 'ChangeUp': {'color': '#8A2BE2', 'marker': 'v'}, 
        'Sinker': {'color': '#FFA500', 'marker': 'v'}, 'TwoSeamFastBall': {'color': '#FF8C00', 'marker': 'o'}, 
    }
    DEFAULT_CONFIG = {'color': '#808080', 'marker': 'o'}

    st.set_page_config(layout="wide", page_title="野球部データ分析ツール")

    # テーブルの見た目調整
    st.markdown("""
        <style>
        div[data-testid="stTable"] table { width: 100% !important; }
        th { white-space: nowrap !important; text-align: center !important; background-color: #f0f2f6 !important; }
        td { text-align: center !important; white-space: nowrap !important; }
        </style>
        """, unsafe_allow_html=True)

    def display_custom_table(df_to_show):
        if df_to_show.empty: return
        format_dict = {col: "{:.1f}" for col in df_to_show.columns if col not in ['球種', '投球割合(球数)']}
        styled_df = df_to_show.style.format(format_dict).hide(axis='index')
        st.write(styled_df.to_html(), unsafe_allow_html=True)

    # ==================================================
    # 2. データ読み込み
    # ==================================================
    DATA_DIR = "data"
    all_data = []
    if os.path.exists(DATA_DIR):
        csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
        for filename in csv_files:
            filepath = os.path.join(DATA_DIR, filename)
            try:
                temp_df = pd.read_csv(filepath)
                temp_df['SeasonFile'] = filename
                all_data.append(temp_df)
            except:
                pass

    if all_data:
        full_df = pd.concat(all_data, ignore_index=True)
        full_df['Pitcher'] = full_df['Pitcher'].astype(str)
        full_df['TaggedPitchType'] = full_df['TaggedPitchType'].replace('FourSeamFastBall', 'Fastball')
        full_df['Date_dt'] = pd.to_datetime(full_df['Date'], errors='coerce')
        full_df = full_df.dropna(subset=['Date_dt'])
        full_df['Date_str'] = full_df['Date_dt'].dt.strftime('%Y-%m-%d')

        # --- サイドバー設定 ---
        st.sidebar.title("設定")
        analysis_mode = st.sidebar.radio("📊 表示モード", ["総合分析（レポート形式）", "1人集中分析", "2人比較（左右）"])
        st.sidebar.markdown("---")

        # 共通のフィルタリング関数
        def get_summary_df(df):
            if df.empty: return pd.DataFrame()
            total = len(df)
            res = df.groupby('TaggedPitchType', observed=True).agg(
                count=('Pitcher', 'count'), 平均球速=('RelSpeed', 'mean'), 最高球速=('RelSpeed', 'max'),
                回転数=('SpinRate', 'mean'), 縦変化量=('InducedVertBreak', 'mean'), 横変化量=('HorzBreak', 'mean'),
                縦リリース=('VertRelAngle', 'mean'), 横リリース=('HorzRelAngle', 'mean')
            ).reset_index()
            res['投球割合(球数)'] = res['count'].apply(lambda x: f"{x/total*100:.1f}% ({x})")
            res['TaggedPitchType'] = pd.Categorical(res['TaggedPitchType'], categories=PITCH_LIST, ordered=True)
            res = res.sort_values('TaggedPitchType').dropna(subset=['TaggedPitchType'])
            res = res[['TaggedPitchType', '投球割合(球数)', '平均球速', '最高球速', '回転数', '縦変化量', '横変化量', '縦リリース', '横リリース']]
            return res.rename(columns={'TaggedPitchType':'球種', '平均球速':'平均球速(km/h)', '最高球速':'最高球速(km/h)', '縦変化量':'縦変化量(cm)', '横変化量':'横変化量(cm)'})

        # --- モード別の表示 ---
        if analysis_mode in ["総合分析（レポート形式）", "1人集中分析"]:
            p1 = st.sidebar.selectbox("分析する投手", sorted(full_df['Pitcher'].unique()))
            p1_all = full_df[full_df['Pitcher'] == p1]
            
            st.sidebar.subheader("絞り込み条件")
            s_files = st.sidebar.multiselect("ファイル選択", sorted(p1_all['SeasonFile'].unique()))
            s_dates = st.sidebar.multiselect("日付選択", sorted(p1_all['Date_str'].unique(), reverse=True))
            
            # フィルタ適用
            p1_df = p1_all.copy()
            if s_files: p1_df = p1_df[p1_df['SeasonFile'].isin(s_files)]
            if s_dates: p1_df = p1_df[p1_df['Date_str'].isin(s_dates)]

            st.header(f"📋 {p1} 投手 分析レポート")
            
            if not p1_df.empty:
                col1, col2, col3 = st.columns([4, 4, 1.2])
                fig1, ax1 = plt.subplots(figsize=(5, 5)); fig2, ax2 = plt.subplots(figsize=(5, 5))
                for pt in PITCH_LIST:
                    d = p1_df[p1_df['TaggedPitchType'] == pt]
                    if not d.empty:
                        cfg = PITCH_CONFIG.get(pt, DEFAULT_CONFIG)
                        ax1.scatter(d['HorzBreak'], d['InducedVertBreak'], color=cfg['color'], marker=cfg['marker'], alpha=0.6)
                        ax2.scatter(d['HorzRelAngle'], d['VertRelAngle'], label=pt, color=cfg['color'], marker=cfg['marker'], alpha=0.6)
                
                for ax, title, lim in zip([ax1, ax2], ["変化量散布図 [cm]", "リリース角度 [度]"], [(-80, 80), (-6, 6)]):
                    ax.set_xlim(lim); ax.set_ylim(lim); ax.set_box_aspect(1); ax.set_title(title); ax.grid(True, alpha=0.2)
                    ax.axvline(0, color='black', lw=1); ax.axhline(0, color='black', lw=1)
                
                with col1: st.pyplot(fig1)
                with col2: st.pyplot(fig2)
                with col3:
                    h, l = ax2.get_legend_handles_labels()
                    if h:
                        fig_l, ax_l = plt.subplots(figsize=(2, 5)); ax_l.legend(h, l, loc='upper left', frameon=False); ax_l.axis('off'); st.pyplot(fig_l)
                
                st.subheader("📊 集計データ")
                display_custom_table(get_summary_df(p1_df))
            else:
                st.info("条件に一致するデータがありません。")

        elif analysis_mode == "2人比較（左右）":
            col_left, col_right = st.sidebar.columns(2)
            p_a = st.sidebar.selectbox("投手 A (左側)", sorted(full_df['Pitcher'].unique()), key="pa")
            p_b = st.sidebar.selectbox("投手 B (右側)", sorted(full_df['Pitcher'].unique()), key="pb")
            
            st.header(f"⚖️ 比較: {p_a} vs {p_b}")
            c1, c2 = st.columns(2)
            with c1:
                st.subheader(f"👤 {p_a}")
                display_custom_table(get_summary_df(full_df[full_df['Pitcher'] == p_a]))
            with c2:
                st.subheader(f"👤 {p_b}")
                display_custom_table(get_summary_df(full_df[full_df['Pitcher'] == p_b]))

    else:
        st.warning("dataフォルダにCSVが見つかりません。")
