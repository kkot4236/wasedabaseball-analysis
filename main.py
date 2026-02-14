import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import os
import numpy as np
import matplotlib.cm as cm

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

    # --- 2. 共通関数（シルエット・ゾーン描画） ---
    def draw_stylish_batter(ax, batter_side='Right'):
        x_offset = 55 if batter_side == 'Right' else -55
        flip = -1 if batter_side == 'Right' else 1
        color = '#333333'
        alpha = 0.1
        ax.add_patch(plt.Circle((x_offset, 135), 6, color=color, alpha=alpha))
        body = plt.Polygon(np.array([[x_offset-10, 80], [x_offset+10, 80], [x_offset+15, 130], [x_offset-15, 130]]), color=color, alpha=alpha)
        ax.add_patch(body)
        bat = plt.Polygon(np.array([[x_offset+(12*flip), 120], [x_offset+(45*flip), 160], [x_offset+(48*flip), 157], [x_offset+(15*flip), 117]]), color=color, alpha=0.15)
        ax.add_patch(bat)

    @st.cache_data
    def load_csv(file_path):
        df = pd.read_csv(file_path)
        # 必要なカラムを数値化
        for c in ['PlateLocSide', 'PlateLocHeight', 'ExitSpeed', 'PitcherThrows']:
            if c in df.columns and c != 'PitcherThrows':
                df[c] = pd.to_numeric(df[c], errors='coerce')
        # ft -> cm 換算 (TrackmanのPlateLocは通常ft単位)
        if 'PlateLocSide' in df.columns and df['PlateLocSide'].abs().max() < 10:
            df['PlateLocSide_cm'] = df['PlateLocSide'] * 30.48
            df['PlateLocHeight_cm'] = df['PlateLocHeight'] * 30.48
        else:
            df['PlateLocSide_cm'] = df['PlateLocSide']
            df['PlateLocHeight_cm'] = df['PlateLocHeight']
        return df

    # --- 3. メインUI構造 ---
    # タブを定義
    tab_p, tab_b = st.tabs(["🔥 投手分析", "⚾ 打者分析"])

    DATA_DIR = "data"
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')] if os.path.exists(DATA_DIR) else []

    if not files:
        st.error("dataフォルダにCSVファイルが見つかりません。")
    else:
        # ---------------------------------------------------------
        # 🔥 投手分析タブ
        # ---------------------------------------------------------
        with tab_p:
            st.sidebar.title("🔥 PITCHER SETTINGS")
            sel_file_p = st.sidebar.selectbox("ファイル選択 (投手)", files, key="p_file")
            df_p = load_csv(os.path.join(DATA_DIR, sel_file_p))
            p_col = 'Pitcher' if 'Pitcher' in df_p.columns else 'Pitcher Name'
            p_list = sorted(df_p[p_col].dropna().unique())
            sel_p = st.sidebar.selectbox("投手を選択", p_list, key="p_sel")
            
            st.title(f"📊 {sel_p} 投手：詳細分析")
            # 投手分析のコード（変化量など）をここに記述

        # ---------------------------------------------------------
        # ⚾ 打者分析タブ
        # ---------------------------------------------------------
        with tab_b:
            st.sidebar.title("⚾ BATTER SETTINGS")
            sel_file_b = st.sidebar.selectbox("ファイル選択 (打者)", files, key="b_file")
            df_b = load_csv(os.path.join(DATA_DIR, sel_file_b))
            b_col = 'Batter' if 'Batter' in df_b.columns else 'Batter Name'
            b_list = sorted(df_b[b_col].dropna().unique())
            sel_b = st.sidebar.selectbox("打者を選択", b_list, key="b_sel")
            v_b = st.sidebar.radio("表示視点", ["投手目線", "捕手目線"], key="b_view")
            
            st.title(f"🎯 {sel_b} 打球速度 9分割分析")

            # データ抽出
            target_df = df_b[df_b[b_col] == sel_b].copy()
            if not target_df.empty:
                batter_hand = target_df['BatterSide'].mode()[0] if 'BatterSide' in target_df.columns else 'Right'
                
                # 集計用フィルタ
                filters = [
                    target_df,
                    target_df[target_df['PitcherThrows'].str.contains('Right|R', na=False)],
                    target_df[target_df['PitcherThrows'].str.contains('Left|L', na=False)]
                ]
                titles = ['TOTAL', 'vs RIGHT P', 'vs LEFT P']

                # 描画 (3カラム)
                cols = st.columns(3)
                # 境界線の設定 (cm) : 9分割用
                # ストライクゾーン: 左右 -21.5~21.5, 高さ 45~105
                x_edges = [-40, -21.5, -7.17, 7.17, 21.5, 40]
                y_edges = [25, 45, 65, 85, 105, 125]
                V_MIN, V_MAX = 110, 160

                for i, ax_col in enumerate(cols):
                    subset = filters[i].dropna(subset=['ExitSpeed', 'PlateLocSide_cm'])
                    fig, ax = plt.subplots(figsize=(6, 8))
                    
                    # 打者シルエット
                    draw_stylish_batter(ax, batter_side=batter_hand)
                    
                    # 5x5 グリッド描画 (中央3x3がストライクゾーン)
                    for r in range(5):
                        for c in range(5):
                            x_min, x_max = x_edges[c], x_edges[c+1]
                            y_min, y_max = y_edges[r], y_edges[r+1]
                            
                            # 視点による左右反転
                            px = subset['PlateLocSide_cm'] * (-1 if v_b == "捕手目線" else 1)
                            py = subset['PlateLocHeight_cm']
                            
                            mask = (px >= x_min) & (px < x_max) & (py >= y_min) & (py < y_max)
                            zone_data = subset[mask]
                            
                            if not zone_data.empty:
                                avg_v = zone_data['ExitSpeed'].mean()
                                count = len(zone_data)
                                color = cm.Reds(np.clip((avg_v - V_MIN) / (V_MAX - V_MIN), 0, 1))
                                
                                ax.add_patch(plt.Rectangle((x_min, y_min), x_max-x_min, y_max-y_min, 
                                             facecolor=color, alpha=0.8, ec='white', lw=0.5))
                                text_color = 'white' if avg_v > 140 else 'black'
                                ax.text((x_min+x_max)/2, (y_min+y_max)/2, f"{avg_v:.1f}\nn={count}", 
                                        ha='center', va='center', fontweight='bold', fontsize=8, color=text_color)

                    # ストライクゾーン枠
                    ax.add_patch(plt.Rectangle((-21.5, 45), 43, 60, fill=False, ec='black', lw=2, zorder=10))
                    ax.set_xlim(-70, 70); ax.set_ylim(10, 160); ax.set_title(titles[i], fontsize=14, fontweight='bold')
                    ax.axis('off')
                    ax_col.pyplot(fig)
            else:
                st.warning("データがありません。")
