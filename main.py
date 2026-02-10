import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import os
import plotly.express as px
import numpy as np

# --- 1. パスワード保護 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = None
    if st.session_state["password_correct"] == True: return True
    def password_entered():
        if st.session_state["password_input"] == "wbc1901":
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False
    st.title("🔐 早稲田大学野球部 データ分析 Pro+")
    st.text_input("パスワードを入力してください", type="password", on_change=password_entered, key="password_input")
    return st.session_state["password_correct"]

if check_password():
    st.set_page_config(layout="wide", page_title="野球部データ分析 Pro+")

    # --- 2. 共通描画関数 ---
    PITCH_LIST = ['Fastball', 'Slider', 'Cutter', 'Curveball', 'Splitter', 'ChangeUp', 'Sinker', 'TwoSeamFastBall']
    PITCH_COLORS = {'Fastball': '#FF4B4B', 'Slider': '#1E90FF', 'Cutter': '#FF1493', 'Curveball': '#32CD32', 'Splitter': '#40E0D0', 'ChangeUp': '#8A2BE2', 'Sinker': '#FFA500', 'TwoSeamFastBall': '#FF8C00'}

    def get_marker(pitch_type, throws):
        if pitch_type == 'Fastball': return 'o'
        if pitch_type in ['Slider', 'Cutter']: return '<' if throws == 'Right' else '>'
        if pitch_type == 'Splitter': return 's'
        if pitch_type in ['ChangeUp', 'Sinker']: return 'v'
        if pitch_type == 'Curveball': return '^'
        return 'o'

    def draw_stylish_batter(ax, batter_side='Right', view_mode="投手目線"):
        if view_mode == "投手目線":
            x_offset, flip = (50, -1) if batter_side == 'Right' else (-50, 1)
        else:
            x_offset, flip = (-50, 1) if batter_side == 'Right' else (50, -1)
        color, alpha = '#333333', 0.12
        ax.add_patch(plt.Circle((x_offset, 130), 5, color=color, alpha=alpha, zorder=0))
        ax.add_patch(plt.Polygon(np.array([[x_offset-8, 80], [x_offset+8, 80], [x_offset+12, 125], [x_offset-12, 125]]), color=color, alpha=alpha))
        ax.add_patch(plt.Polygon(np.array([[x_offset+(10*flip), 115], [x_offset+(40*flip), 155], [x_offset+(43*flip), 152], [x_offset+(13*flip), 112]]), color=color, alpha=0.18))

    # --- 3. データ読み込み ---
    @st.cache_data
    def load_data():
        DATA_DIR = "data"
        all_data = []
        if os.path.exists(DATA_DIR):
            for f in [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]:
                try:
                    df = pd.read_csv(os.path.join(DATA_DIR, f))
                    cols = ['RelSpeed', 'InducedVertBreak', 'HorzBreak', 'RelHeight', 'RelSide', 'Extension', 'PlateLocSide', 'PlateLocHeight', 'ExitSpeed']
                    for c in cols:
                        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
                    for c in ['RelHeight', 'RelSide', 'Extension', 'PlateLocSide', 'PlateLocHeight']:
                        if c in df.columns: df[c] *= 100
                    df['SeasonFile'] = f
                    all_data.append(df)
                except: pass
        return pd.concat(all_data, ignore_index=True) if all_data else None

    full_df = load_data()

    if full_df is not None:
        full_df['TaggedPitchType'] = full_df['TaggedPitchType'].replace('FourSeamFastBall', 'Fastball').fillna('Unknown')
        full_df['Date_str'] = pd.to_datetime(full_df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
        p_col = 'Pitcher' if 'Pitcher' in full_df.columns else 'Pitcher Name'
        b_col = 'Batter Name' if 'Batter Name' in full_df.columns else 'Batter'

        # --- 4. モード切り替え (タブによる制御) ---
        mode = st.radio("🏠 モード選択", ["🔥 投手分析", "⚾ 打者分析"], horizontal=True, label_visibility="collapsed")

        # --- 5. サイドバーとメイン画面の連動 ---
        if mode == "🔥 投手分析":
            # 投手用サイドバー
            st.sidebar.title("🔥 PITCHER MENU")
            p_list = sorted(full_df[p_col].dropna().unique())
            sel_p = st.sidebar.selectbox("投手を選択", p_list)
            p_report = st.sidebar.radio("形式", ["総合レポート", "詳細分析"])
            
            p_df = full_df[full_df[p_col] == sel_p].copy()
            st.sidebar.info(f"投球数: {len(p_df)}")

            # 投手メイン画面
            st.header(f"📊 {sel_p} 投手：分析")
            c1, c2 = st.columns(2)
            with c1:
                fig, ax = plt.subplots(); ax.axvline(0, color='k'); ax.axhline(0, color='k')
                for pt in p_df['TaggedPitchType'].unique():
                    d = p_df[p_df['TaggedPitchType']==pt]
                    ax.scatter(d['HorzBreak'], d['InducedVertBreak'], label=pt, color=PITCH_COLORS.get(pt, 'gray'), alpha=0.5)
                ax.set_xlim(-80, 80); ax.set_ylim(-80, 80); ax.set_title("変化量 (cm)"); st.pyplot(fig)
            with c2:
                st.write("### 球種別平均")
                st.dataframe(p_df.groupby('TaggedPitchType')['RelSpeed'].agg(['count', 'mean']).round(1))

        elif mode == "⚾ 打者分析":
            # 打者用サイドバー
            st.sidebar.title("⚾ BATTER MENU")
            b_list = sorted(full_df[b_col].dropna().unique())
            sel_b = st.sidebar.selectbox("打者を分析", b_list)
            v_mode = st.sidebar.radio("表示視点", ["投手目線", "捕手目線"])
            
            b_df = full_df[full_df[b_col] == sel_b].copy()
            st.sidebar.success(f"打席データ数: {len(b_df)}")

            # 打者メイン画面
            st.header(f"🎯 {sel_b} 打者：打球速度ヒートマップ")
            
            if not b_df.empty:
                b_df['PlateLocSide_Plot'] = b_df['PlateLocSide'] * (-1 if v_mode == "捕手目線" else 1)
                b_hand = b_df['BatterSide'].mode()[0] if not b_df['BatterSide'].dropna().empty else 'Right'
                
                # エッジ設定
                x_edges = [-36.5, -21.5, -7.17, 7.17, 21.5, 36.5]
                y_edges = [30.0, 45.0, 65.0, 85.0, 105.0, 120.0]

                # --- 色調整のポイント ---
                # 130km/h台を薄くするため、V_MINを少し上げ、V_MAXとの幅を調整
                V_MIN, V_MAX = 100, 165 

                fig_h, axes_h = plt.subplots(1, 3, figsize=(20, 8), facecolor='white')
                filters_h = [b_df, b_df[b_df['PitcherThrows'] == 'Right'], b_df[b_df['PitcherThrows'] == 'Left']]
                titles_h = ['TOTAL', 'VS RIGHT P', 'VS LEFT P']

                for i, ax in enumerate(axes_h):
                    subset_h = filters_h[i]
                    draw_stylish_batter(ax, b_hand, v_mode)
                    for r in range(5):
                        for c in range(5):
                            x_min, x_max = x_edges[c], x_edges[c+1]
                            y_min, y_max = y_edges[4-r], y_edges[5-r]
                            zone_data = subset_h[(subset_h['PlateLocSide_Plot'] >= x_min) & (subset_h['PlateLocSide_Plot'] < x_max) &
                                                (subset_h['PlateLocHeight'] >= y_min) & (subset_h['PlateLocHeight'] < y_max)]
                            
                            if not zone_data.empty:
                                avg_v = zone_data['ExitSpeed'].mean()
                                if pd.notna(avg_v):
                                    # 正規化の計算を調整（130だと約0.46になり、薄い赤色になる）
                                    norm = (avg_v - V_MIN) / (V_MAX - V_MIN)
                                    color = plt.cm.Reds(np.clip(norm, 0, 1))
                                    ax.add_patch(plt.Rectangle((x_min, y_min), x_max-x_min, y_max-y_min, color=color, alpha=0.9, ec='white', lw=0.5))
                                    # テキスト色の反転基準
                                    t_color = 'white' if norm > 0.7 else 'black'
                                    ax.text((x_min + x_max)/2, (y_min + y_max)/2, f"{avg_v:.1f}\n$n$={len(zone_data)}", ha='center', va='center', fontsize=8, color=t_color, fontweight='bold')

                    ax.add_patch(plt.Rectangle((-21.5, 45.0), 43.0, 60.0, fill=False, edgecolor='black', lw=2))
                    ax.set_xlim(-80, 80); ax.set_ylim(10, 160); ax.set_aspect('equal'); ax.axis('off'); ax.set_title(titles_h[i])
                st.pyplot(fig_h)
            else:
                st.warning("データがありません。")

    else:
        st.error("dataフォルダにCSVが見つかりません。")
