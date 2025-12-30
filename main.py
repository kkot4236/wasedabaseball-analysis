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
        st.session_state["password_correct"] = None
    if st.session_state["password_correct"] == True:
        return True

    def password_entered():
        if st.session_state["password_input"] == "waseda123":
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False

    st.title("🔐 早稲田大学野球部 データ分析ツール")
    st.text_input("パスワードを入力してください", type="password", on_change=password_entered, key="password_input")
    if st.session_state["password_correct"] == False:
        st.error("😕 パスワードが違います。")
    return False

if check_password():
    # ==================================================
    # 1. 基本設定 & 関数定義
    # ==================================================
    st.set_page_config(layout="wide", page_title="野球部データ分析ツール")

    PITCH_LIST = ['Fastball', 'Slider', 'Cutter', 'Curveball', 'Splitter', 'ChangeUp', 'Sinker', 'TwoSeamFastBall']
    PITCH_CONFIG = {
        'Fastball': {'color': '#FF4B4B', 'marker': 'o'}, 'Slider': {'color': '#1E90FF', 'marker': '<'}, 
        'Cutter': {'color': '#FF1493', 'marker': 's'}, 'Curveball': {'color': '#32CD32', 'marker': '^'}, 
        'Splitter': {'color': '#40E0D0', 'marker': 's'}, 'ChangeUp': {'color': '#8A2BE2', 'marker': 'v'}, 
        'Sinker': {'color': '#FFA500', 'marker': 'v'}, 'TwoSeamFastBall': {'color': '#FF8C00', 'marker': 'o'}, 
    }
    DEFAULT_CONFIG = {'color': '#808080', 'marker': 'o'}

    def display_custom_table(df_to_show):
        if df_to_show.empty: return
        format_dict = {col: "{:.1f}" for col in df_to_show.columns if col not in ['球種', '投球割合(球数)']}
        styled_df = df_to_show.style.format(format_dict).hide(axis='index')
        st.write(styled_df.to_html(), unsafe_allow_html=True)

    def get_summary_df(df):
        if df.empty: return pd.DataFrame()
        total = len(df)
        res = df.groupby('TaggedPitchType', observed=True).agg(
            count=('Pitcher', 'count'), 平均球速=('RelSpeed', 'mean'), 最高球速=('RelSpeed', 'max'),
            回転数=('SpinRate', 'mean'), 縦変化量=('InducedVertBreak', 'mean'), 横変化量=('HorzBreak', 'mean')
        ).reset_index()
        res['投球割合(球数)'] = res['count'].apply(lambda x: f"{x/total*100:.1f}% ({x})")
        res['TaggedPitchType'] = pd.Categorical(res['TaggedPitchType'], categories=PITCH_LIST, ordered=True)
        res = res.sort_values('TaggedPitchType').dropna(subset=['TaggedPitchType'])
        res = res[['TaggedPitchType', '投球割合(球数)', '平均球速', '最高球速', '回転数', '縦変化量', '横変化量']]
        return res.rename(columns={'TaggedPitchType':'球種', '平均球速':'平均(km/h)', '最高球速':'最高(km/h)', '縦変化量':'縦変化(cm)', '横変化量':'横変化(cm)'})

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
            except: pass

    if all_data:
        full_df = pd.concat(all_data, ignore_index=True)
        full_df['Pitcher'] = full_df['Pitcher'].astype(str)
        full_df['TaggedPitchType'] = full_df['TaggedPitchType'].replace('FourSeamFastBall', 'Fastball')
        full_df['Date_dt'] = pd.to_datetime(full_df['Date'], errors='coerce')
        full_df = full_df.dropna(subset=['Date_dt'])
        full_df['Date_str'] = full_df['Date_dt'].dt.strftime('%Y-%m-%d')

        st.sidebar.title("📊 MENU")
        mode = st.sidebar.radio("モード選択", ["総合レポート", "1人集中分析", "2人比較"])
        st.sidebar.markdown("---")

        # ==================================================
        # 3. モード別の処理
        # ==================================================
        # 共通のフィルターUI
        p1 = st.sidebar.selectbox("投手を選択", sorted(full_df['Pitcher'].unique()))
        p1_all = full_df[full_df['Pitcher'] == p1]
        
        # 総合レポートでも絞り込みができるように配置
        st.sidebar.subheader("データ絞り込み")
        s_files = st.sidebar.multiselect("ファイル選択", sorted(p1_all['SeasonFile'].unique()))
        s_dates = st.sidebar.multiselect("日付選択", sorted(p1_all['Date_str'].unique(), reverse=True))
        
        target_df = p1_all.copy()
        if s_files: target_df = target_df[target_df['SeasonFile'].isin(s_files)]
        if s_dates: target_df = target_df[target_df['Date_str'].isin(s_dates)]

        if mode == "総合レポート":
            st.header(f"📋 {p1} 投手：総合レポート")
            # 変化量とリリースの2画面を表示
            col1, col2 = st.columns(2)
            fig1, ax1 = plt.subplots(figsize=(5, 5)); fig2, ax2 = plt.subplots(figsize=(5, 5))
            for pt in PITCH_LIST:
                d = target_df[target_df['TaggedPitchType'] == pt]
                if not d.empty:
                    cfg = PITCH_CONFIG.get(pt, DEFAULT_CONFIG)
                    ax1.scatter(d['HorzBreak'], d['InducedVertBreak'], color=cfg['color'], marker=cfg['marker'], alpha=0.6)
                    ax2.scatter(d['HorzRelAngle'], d['VertRelAngle'], label=pt, color=cfg['color'], marker=cfg['marker'], alpha=0.6)
            for ax, title, lim in zip([ax1, ax2], ["変化量散布図 [cm]", "リリース角度散布図 [度]"], [(-80, 80), (-6, 6)]):
                ax.set_xlim(lim); ax.set_ylim(lim); ax.set_title(title); ax.grid(True, alpha=0.2); ax.axvline(0, color='black'); ax.axhline(0, color='black')
            with col1: st.pyplot(fig1)
            with col2: st.pyplot(fig2)
            st.subheader("📊 集計データ")
            display_custom_table(get_summary_df(target_df))

        elif mode == "1人集中分析":
            st.sidebar.subheader("表示項目の選択")
            show_brk = st.sidebar.checkbox("変化量 (Break)", value=True)
            show_ang = st.sidebar.checkbox("リリースアングル (Angle)", value=True)
            show_loc = st.sidebar.checkbox("到達位置 (PlateLoc - 左右別)", value=True)
            show_pos = st.sidebar.checkbox("リリース位置 (RelPos)", value=True)
            show_table = st.sidebar.checkbox("集計データ表", value=True)

            st.header(f"👤 {p1} 投手：集中分析")

            # チェックされた項目だけ表示
            if show_brk:
                st.subheader("■ 変化量散布図")
                fig, ax = plt.subplots(figsize=(6, 5))
                for pt in PITCH_LIST:
                    d = target_df[target_df['TaggedPitchType'] == pt]
                    if not d.empty:
                        cfg = PITCH_CONFIG.get(pt, DEFAULT_CONFIG)
                        ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=cfg['color'], marker=cfg['marker'], label=pt, alpha=0.6)
                ax.set_xlim(-80, 80); ax.set_ylim(-80, 80); ax.axvline(0, color='black'); ax.axhline(0, color='black'); ax.grid(True, alpha=0.2); ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                st.pyplot(fig)

            if show_ang:
                st.subheader("■ リリースアングル")
                fig, ax = plt.subplots(figsize=(6, 5))
                for pt in PITCH_LIST:
                    d = target_df[target_df['TaggedPitchType'] == pt]
                    if not d.empty:
                        cfg = PITCH_CONFIG.get(pt, DEFAULT_CONFIG)
                        ax.scatter(d['HorzRelAngle'], d['VertRelAngle'], color=cfg['color'], marker=cfg['marker'], label=pt, alpha=0.6)
                ax.set_xlim(-6, 6); ax.set_ylim(-6, 6); ax.axvline(0, color='black'); ax.axhline(0, color='black'); ax.grid(True, alpha=0.2); ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                st.pyplot(fig)

            if show_loc:
                st.subheader("■ 到達位置 (PlateLoc) - 左: 対右打者 / 右: 対左打者")
                col_r, col_l = st.columns(2)
                for side, col, title in [('Right', col_r, '対 右打者'), ('Left', col_l, '対 左打者')]:
                    with col:
                        fig, ax = plt.subplots(figsize=(5, 6))
                        ax.add_patch(plt.Rectangle((-25, 45), 50, 60, fill=False, color='black', lw=2)) # ストライクゾーン
                        d_side = target_df[target_df['BatterSide'] == side]
                        for pt in PITCH_LIST:
                            d_pt = d_side[d_side['TaggedPitchType'] == pt]
                            if not d_pt.empty:
                                cfg = PITCH_CONFIG.get(pt, DEFAULT_CONFIG)
                                ax.scatter(d_pt['PlateLocSide'], d_pt['PlateLocHeight'], color=cfg['color'], marker=cfg['marker'], alpha=0.6)
                        ax.set_xlim(-100, 100); ax.set_ylim(0, 200); ax.set_title(title); ax.set_aspect('equal'); ax.grid(True, alpha=0.2)
                        st.pyplot(fig)

            if show_pos:
                st.subheader("■ リリース位置 (RelPos)")
                fig, ax = plt.subplots(figsize=(6, 5))
                for pt in PITCH_LIST:
                    d = target_df[target_df['TaggedPitchType'] == pt]
                    if not d.empty:
                        cfg = PITCH_CONFIG.get(pt, DEFAULT_CONFIG)
                        ax.scatter(d['RelPosSide'], d['RelPosHeight'], color=cfg['color'], marker=cfg['marker'], label=pt, alpha=0.6)
                ax.set_xlim(-150, 150); ax.set_ylim(0, 250); ax.axvline(0, color='black'); ax.grid(True, alpha=0.2); ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                st.pyplot(fig)

            if show_table:
                st.subheader("📊 分析スタッツ")
                display_custom_table(get_summary_df(target_df))

        elif mode == "2人比較":
            pb = st.sidebar.selectbox("比較対象(投手B)を選択", sorted(full_df['Pitcher'].unique()), key="pb")
            st.header(f"⚖️ {p1} vs {pb}")
            c1, c2 = st.columns(2)
            with c1: st.subheader(p1); display_custom_table(get_summary_df(target_df))
            with c2: st.subheader(pb); display_custom_table(get_summary_df(full_df[full_df['Pitcher'] == pb]))
    else:
        st.warning("dataフォルダにCSVが見つかりません。")
