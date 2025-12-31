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
    st.set_page_config(layout="wide", page_title="野球部データ分析ツール")

    PITCH_LIST = ['Fastball', 'Slider', 'Cutter', 'Curveball', 'Splitter', 'ChangeUp', 'Sinker', 'TwoSeamFastBall']
    PITCH_CONFIG = {
        'Fastball': {'color': '#FF4B4B', 'marker': 'o'}, 'Slider': {'color': '#1E90FF', 'marker': '<'}, 
        'Cutter': {'color': '#FF1493', 'marker': 's'}, 'Curveball': {'color': '#32CD32', 'marker': '^'}, 
        'Splitter': {'color': '#40E0D0', 'marker': 's'}, 'ChangeUp': {'color': '#8A2BE2', 'marker': 'v'}, 
        'Sinker': {'color': '#FFA500', 'marker': 'v'}, 'TwoSeamFastBall': {'color': '#FF8C00', 'marker': 'o'}, 
    }

    # 表の表示をきれいにする関数
    def display_mini_table(df, cols_rename):
        if df.empty: return
        res = df.groupby('TaggedPitchType', observed=True).agg({k: 'mean' for k in cols_rename.keys()}).reset_index()
        res['TaggedPitchType'] = pd.Categorical(res['TaggedPitchType'], categories=PITCH_LIST, ordered=True)
        res = res.sort_values('TaggedPitchType').dropna(subset=['TaggedPitchType'])
        res = res.rename(columns={'TaggedPitchType': '球種', **cols_rename})
        st.dataframe(res.style.format(precision=1), use_container_width=True)

    # データ読み込み
    DATA_DIR = "data"
    all_data = []
    if os.path.exists(DATA_DIR):
        csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
        for filename in csv_files:
            filepath = os.path.join(DATA_DIR, filename)
            try:
                temp_df = pd.read_csv(filepath)
                # 単位変換
                for col in ['PlateLocSide', 'PlateLocHeight', 'RelPosSide', 'RelPosHeight']:
                    if col in temp_df.columns: temp_df[col] = temp_df[col] * 100
                temp_df['SeasonFile'] = filename
                all_data.append(temp_df)
            except: pass

    if all_data:
        full_df = pd.concat(all_data, ignore_index=True)
        full_df['TaggedPitchType'] = full_df['TaggedPitchType'].replace('FourSeamFastBall', 'Fastball')
        full_df['Date_str'] = pd.to_datetime(full_df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')

        st.sidebar.title("📊 MENU")
        mode = st.sidebar.radio("モード選択", ["1人集中分析", "総合レポート", "2人比較"])
        
        p1 = st.sidebar.selectbox("投手を選択", sorted(full_df['Pitcher'].unique().astype(str)))
        p1_df = full_df[full_df['Pitcher'].astype(str) == p1]

        st.sidebar.subheader("📅 絞り込み")
        s_files = st.sidebar.multiselect("ファイル選択", sorted(p1_df['SeasonFile'].unique()))
        s_dates = st.sidebar.multiselect("日付選択", sorted(p1_df['Date_str'].dropna().unique(), reverse=True))
        
        target_df = p1_df.copy()
        if s_files: target_df = target_df[target_df['SeasonFile'].isin(s_files)]
        if s_dates: target_df = target_df[target_df['Date_str'].isin(s_dates)]

        if mode == "1人集中分析":
            st.sidebar.subheader("👁 表示項目の選択")
            show_brk = st.sidebar.checkbox("変化量 (Break)", value=False)
            show_ang = st.sidebar.checkbox("リリースアングル (Angle)", value=False)
            show_loc = st.sidebar.checkbox("到達位置 (PlateLoc)", value=False)
            show_pos = st.sidebar.checkbox("リリース位置 (RelPos)", value=False)

            st.header(f"👤 {p1} 投手：集中分析")

            # 1. 変化量
            if show_brk:
                st.subheader("■ 変化量散布図 [cm]")
                fig, ax = plt.subplots(figsize=(8, 5))
                for pt in PITCH_LIST:
                    d = target_df[target_df['TaggedPitchType'] == pt]
                    if not d.empty:
                        ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_CONFIG[pt]['color'], label=pt, alpha=0.6)
                ax.set_xlim(-80, 80); ax.set_ylim(-80, 80); ax.axvline(0, color='black'); ax.axhline(0, color='black'); ax.grid(True, alpha=0.3); ax.legend(loc='upper left', bbox_to_anchor=(1,1))
                st.pyplot(fig)
                display_mini_table(target_df, {'InducedVertBreak': '縦変化(cm)', 'HorzBreak': '横変化(cm)'})

            # 2. リリースアングル
            if show_ang:
                st.subheader("■ リリースアングル [度]")
                fig, ax = plt.subplots(figsize=(8, 5))
                for pt in PITCH_LIST:
                    d = target_df[target_df['TaggedPitchType'] == pt]
                    if not d.empty:
                        ax.scatter(d['HorzRelAngle'], d['VertRelAngle'], color=PITCH_CONFIG[pt]['color'], label=pt, alpha=0.6)
                ax.set_xlim(-6, 6); ax.set_ylim(-6, 6); ax.axvline(0, color='black'); ax.axhline(0, color='black'); ax.grid(True, alpha=0.3); ax.legend(loc='upper left', bbox_to_anchor=(1,1))
                st.pyplot(fig)
                display_mini_table(target_df, {'VertRelAngle': 'リリースアングル(縦)', 'HorzRelAngle': 'リリースアングル(横)'})

            # 3. 到達位置
            if show_loc:
                st.subheader("■ 到達位置 [cm]")
                c1, c2 = st.columns(2)
                for side, col, title in [('Right', c1, '対 右打者'), ('Left', c2, '対 左打者')]:
                    with col:
                        fig, ax = plt.subplots(figsize=(5, 6))
                        ax.add_patch(plt.Rectangle((-25, 45), 50, 60, fill=False, lw=2))
                        d_s = target_df[target_df['BatterSide'] == side]
                        for pt in PITCH_LIST:
                            d_p = d_s[d_s['TaggedPitchType'] == pt]
                            if not d_p.empty: ax.scatter(d_p['PlateLocSide'], d_p['PlateLocHeight'], color=PITCH_CONFIG[pt]['color'], alpha=0.6)
                        ax.set_xlim(-100, 100); ax.set_ylim(0, 200); ax.set_title(title); ax.set_aspect('equal'); st.pyplot(fig)
                display_mini_table(target_df, {'PlateLocHeight': '到達高さ(cm)', 'PlateLocSide': '到達横位置(cm)'})

            # 4. リリース位置 (エラー対策)
            if show_pos:
                st.subheader("■ リリース位置 [cm]")
                if 'RelPosSide' in target_df.columns and 'RelPosHeight' in target_df.columns:
                    fig, ax = plt.subplots(figsize=(8, 5))
                    for pt in PITCH_LIST:
                        d = target_df[target_df['TaggedPitchType'] == pt]
                        if not d.empty:
                            ax.scatter(d['RelPosSide'], d['RelPosHeight'], color=PITCH_CONFIG[pt]['color'], label=pt, alpha=0.6)
                    ax.set_xlim(-150, 150); ax.set_ylim(0, 250); ax.axvline(0, color='black'); ax.grid(True, alpha=0.3); ax.legend(loc='upper left', bbox_to_anchor=(1,1))
                    st.pyplot(fig)
                    display_mini_table(target_df, {'RelPosHeight': 'リリース高(cm)', 'RelPosSide': 'リリースサイド(cm)'})
                else:
                    st.error("データ内にリリース位置（RelPos）のカラムが見つかりません。")

        elif mode == "総合レポート":
            st.header(f"📋 {p1} 投手：総合レポート")
            # 変化量とアングルを並べて表示
            col1, col2 = st.columns(2)
            with col1:
                fig, ax = plt.subplots(figsize=(5, 5))
                for pt in PITCH_LIST:
                    d = target_df[target_df['TaggedPitchType'] == pt]
                    if not d.empty: ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_CONFIG[pt]['color'], alpha=0.6)
                ax.set_xlim(-80, 80); ax.set_ylim(-80, 80); ax.set_title("変化量"); ax.grid(True, alpha=0.2); st.pyplot(fig)
            with col2:
                fig, ax = plt.subplots(figsize=(5, 5))
                for pt in PITCH_LIST:
                    d = target_df[target_df['TaggedPitchType'] == pt]
                    if not d.empty: ax.scatter(d['HorzRelAngle'], d['VertRelAngle'], color=PITCH_CONFIG[pt]['color'], alpha=0.6)
                ax.set_xlim(-6, 6); ax.set_ylim(-6, 6); ax.set_title("リリースアングル"); ax.grid(True, alpha=0.2); st.pyplot(fig)
            
            # 総合スタッツ
            res = target_df.groupby('TaggedPitchType', observed=True).agg({'RelSpeed':'mean', 'SpinRate':'mean', 'InducedVertBreak':'mean', 'HorzBreak':'mean', 'VertRelAngle':'mean', 'HorzRelAngle':'mean'}).reset_index()
            res = res.rename(columns={'RelSpeed':'球速', 'SpinRate':'回転数', 'InducedVertBreak':'縦変化', 'HorzBreak':'横変化', 'VertRelAngle':'アングル縦', 'HorzRelAngle':'アングル横'})
            st.dataframe(res.style.format(precision=1), use_container_width=True)

    else:
        st.warning("dataフォルダにCSVが見つかりません。")
