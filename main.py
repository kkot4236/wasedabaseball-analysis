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
    # 1. 基本設定
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
            回転数=('SpinRate', 'mean'), 縦変化量=('InducedVertBreak', 'mean'), 横変化量=('HorzBreak', 'mean'),
            縦アングル=('VertRelAngle', 'mean'), 横アングル=('HorzRelAngle', 'mean')
        ).reset_index()
        res['投球割合(球数)'] = res['count'].apply(lambda x: f"{x/total*100:.1f}% ({x})")
        res['TaggedPitchType'] = pd.Categorical(res['TaggedPitchType'], categories=PITCH_LIST, ordered=True)
        res = res.sort_values('TaggedPitchType').dropna(subset=['TaggedPitchType'])
        res = res[['TaggedPitchType', '投球割合(球数)', '平均球速', '最高球速', '回転数', '縦変化量', '横変化量', '縦アングル', '横アングル']]
        return res.rename(columns={
            'TaggedPitchType':'球種', '平均球速':'平均(km/h)', '最高球速':'最高(km/h)', 
            '縦変化量':'縦変化(cm)', '横変化量':'横変化(cm)', 
            '縦アングル':'リリースアングル(縦)', '横アングル':'リリースアングル(横)'
        })

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
                # m -> cm 変換
                for col in ['PlateLocSide', 'PlateLocHeight', 'RelPosSide', 'RelPosHeight']:
                    if col in temp_df.columns:
                        temp_df[col] = temp_df[col] * 100
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

        # 共通フィルターUI（基本は投手Aの設定）
        p1 = st.sidebar.selectbox("投手Aを選択", sorted(full_df['Pitcher'].unique()), key="p1_sel")
        p1_all = full_df[full_df['Pitcher'] == p1]
        
        # 共通のグラフ描画関数
        def plot_scatter(df, mode_type, title_suffix=""):
            fig, ax = plt.subplots(figsize=(5, 5))
            for pt in PITCH_LIST:
                d = df[df['TaggedPitchType'] == pt]
                if not d.empty:
                    cfg = PITCH_CONFIG.get(pt, DEFAULT_CONFIG)
                    if mode_type == "break":
                        ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=cfg['color'], marker=cfg['marker'], alpha=0.6)
                        ax.set_xlim(-80, 80); ax.set_ylim(-80, 80)
                    elif mode_type == "angle":
                        ax.scatter(d['HorzRelAngle'], d['VertRelAngle'], color=cfg['color'], marker=cfg['marker'], alpha=0.6)
                        ax.set_xlim(-6, 6); ax.set_ylim(-6, 6)
                    elif mode_type == "pos":
                        ax.scatter(d['RelPosSide'], d['RelPosHeight'], color=cfg['color'], marker=cfg['marker'], alpha=0.6)
                        ax.set_xlim(-150, 150); ax.set_ylim(0, 250)
            ax.axvline(0, color='black', lw=1); ax.axhline(0, color='black', lw=1); ax.grid(True, alpha=0.2)
            ax.set_title(title_suffix)
            return fig

        if mode == "総合レポート":
            st.header(f"📋 {p1} 投手：総合レポート")
            col1, col2 = st.columns(2)
            with col1: st.pyplot(plot_scatter(p1_all, "break", "変化量散布図 [cm]"))
            with col2: st.pyplot(plot_scatter(p1_all, "angle", "リリースアングル [度]"))
            st.subheader("📊 総合スタッツ")
            display_custom_table(get_summary_df(p1_all))

        elif mode == "1人集中分析" or mode == "2人比較":
            st.sidebar.subheader("表示項目の選択")
            show_brk = st.sidebar.checkbox("変化量 (Break)", value=False)
            show_ang = st.sidebar.checkbox("リリースアングル (Angle)", value=False)
            show_loc = st.sidebar.checkbox("到達位置 (PlateLoc)", value=False)
            show_pos = st.sidebar.checkbox("リリース位置 (RelPos)", value=False)
            show_table = st.sidebar.checkbox("集計データ表", value=False)

            if mode == "1人集中分析":
                st.header(f"👤 {p1} 投手：集中分析")
                s_files = st.sidebar.multiselect("ファイル絞り込み", sorted(p1_all['SeasonFile'].unique()))
                target_df = p1_all[p1_all['SeasonFile'].isin(s_files)] if s_files else p1_all
                
                col_a, col_b = st.columns(2)
                if show_brk: 
                    with col_a: st.pyplot(plot_scatter(target_df, "break", "変化量 [cm]"))
                if show_ang: 
                    with col_b: st.pyplot(plot_scatter(target_df, "angle", "リリースアングル [度]"))
                if show_loc:
                    st.subheader("■ 到達位置 [cm] (左:対右 / 右:対左)")
                    c_r, c_l = st.columns(2)
                    for s, c, t in [('Right', c_r, '対右'), ('Left', c_l, '対左')]:
                        with c:
                            fig, ax = plt.subplots(figsize=(5, 5))
                            ax.add_patch(plt.Rectangle((-25, 45), 50, 60, fill=False, color='black', lw=2))
                            d_s = target_df[target_df['BatterSide'] == s]
                            for pt in PITCH_LIST:
                                d_p = d_s[d_s['TaggedPitchType'] == pt]
                                if not d_p.empty: ax.scatter(d_p['PlateLocSide'], d_p['PlateLocHeight'], color=PITCH_CONFIG.get(pt)['color'], alpha=0.6)
                            ax.set_xlim(-100, 100); ax.set_ylim(0, 200); ax.set_title(t); ax.set_aspect('equal'); st.pyplot(fig)
                if show_pos:
                    with col_a: st.pyplot(plot_scatter(target_df, "pos", "リリース位置 [cm]"))
                if show_table: display_custom_table(get_summary_df(target_df))

            else: # 2人比較モード
                p2 = st.sidebar.selectbox("投手Bを選択", sorted(full_df['Pitcher'].unique()), key="p2_sel")
                p2_all = full_df[full_df['Pitcher'] == p2]
                st.header(f"⚖️ 比較: {p1} vs {p2}")
                
                c_left, c_right = st.columns(2)
                if show_brk:
                    with c_left: st.pyplot(plot_scatter(p1_all, "break", f"{p1}: 変化量"))
                    with c_right: st.pyplot(plot_scatter(p2_all, "break", f"{p2}: 変化量"))
                if show_ang:
                    with c_left: st.pyplot(plot_scatter(p1_all, "angle", f"{p1}: アングル"))
                    with c_right: st.pyplot(plot_scatter(p2_all, "angle", f"{p2}: アングル"))
                if show_loc:
                    st.subheader("■ 到達位置 比較 (対右打者)")
                    with c_left:
                        fig, ax = plt.subplots(figsize=(5, 5)); ax.add_patch(plt.Rectangle((-25, 45), 50, 60, fill=False)); d_s = p1_all[p1_all['BatterSide'] == 'Right']
                        for pt in PITCH_LIST:
                            d_p = d_s[d_s['TaggedPitchType'] == pt]
                            if not d_p.empty: ax.scatter(d_p['PlateLocSide'], d_p['PlateLocHeight'], color=PITCH_CONFIG.get(pt)['color'], alpha=0.6)
                        ax.set_xlim(-100, 100); ax.set_ylim(0, 200); ax.set_title(f"{p1}: 対右"); st.pyplot(fig)
                    with c_right:
                        fig, ax = plt.subplots(figsize=(5, 5)); ax.add_patch(plt.Rectangle((-25, 45), 50, 60, fill=False)); d_s = p2_all[p2_all['BatterSide'] == 'Right']
                        for pt in PITCH_LIST:
                            d_p = d_s[d_s['TaggedPitchType'] == pt]
                            if not d_p.empty: ax.scatter(d_p['PlateLocSide'], d_p['PlateLocHeight'], color=PITCH_CONFIG.get(pt)['color'], alpha=0.6)
                        ax.set_xlim(-100, 100); ax.set_ylim(0, 200); ax.set_title(f"{p2}: 対右"); st.pyplot(fig)
                if show_table:
                    with c_left: st.subheader(p1); display_custom_table(get_summary_df(p1_all))
                    with c_right: st.subheader(p2); display_custom_table(get_summary_df(p2_all))
    else:
        st.warning("dataフォルダにCSVが見つかりません。")
