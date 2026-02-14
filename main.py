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

    def draw_stylish_batter(ax, batter_side='Right'):
        x_offset = 50 if batter_side == 'Right' else -50
        flip = -1 if batter_side == 'Right' else 1
        color = '#333333'; alpha = 0.12
        ax.add_patch(plt.Circle((x_offset, 130), 5, color=color, alpha=alpha, zorder=0))
        body = plt.Polygon(np.array([[x_offset-8, 80], [x_offset+8, 80], [x_offset+12, 125], [x_offset-12, 125]]), color=color, alpha=alpha, zorder=0)
        ax.add_patch(body)
        ax.add_patch(plt.Polygon(np.array([[x_offset-8, 80], [x_offset-4, 80], [x_offset-12, 20], [x_offset-20, 20]]), color=color, alpha=alpha, zorder=0))
        ax.add_patch(plt.Polygon(np.array([[x_offset+4, 80], [x_offset+8, 80], [x_offset+15, 20], [x_offset+8, 20]]), color=color, alpha=alpha, zorder=0))
        bat = plt.Polygon(np.array([[x_offset+(10*flip), 115], [x_offset+(40*flip), 155], [x_offset+(43*flip), 152], [x_offset+(13*flip), 112]]), color=color, alpha=0.18, zorder=0)
        ax.add_patch(bat)

    @st.cache_data
    def load_csv(file_path):
        try: df = pd.read_csv(file_path, encoding='cp932')
        except: df = pd.read_csv(file_path, encoding='utf-8')
        df['PlateLocSide_cm'] = df['PlateLocSide'] * 100
        df['PlateLocHeight_cm'] = df['PlateLocHeight'] * 100
        return df

    mode = st.sidebar.radio("🔥 分析モード", ["投手分析", "打者分析"])
    DATA_DIR = "data"
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')] if os.path.exists(DATA_DIR) else []

    if files:
        if mode == "打者分析":
            with st.sidebar:
                st.header("⚾ BATTER SETTINGS")
                sel_file = st.selectbox("ファイルを選択", files, key="b_f")
                df_b = load_csv(os.path.join(DATA_DIR, sel_file))
                b_col = 'Batter' if 'Batter' in df_b.columns else 'Batter Name'
                sel_b = st.selectbox("打者を選択", sorted(df_b[b_col].dropna().unique()), key="b_s")
                v_view = st.radio("表示視点", ["投手目線", "捕手目線"])
                st.markdown("---")
                target_col = st.selectbox("表示項目を選択", ["打球速度", "打球角度", "飛距離"])
                col_map = {"打球速度": "ExitSpeed", "打球角度": "Angle", "飛距離": "Distance"}
                data_col = col_map[target_col]

            # --- 1. コース別ヒートマップ（既存通り） ---
            st.title(f"🎯 {sel_b} 分析レポート")
            target_df = df_b[(df_b[b_col] == sel_b) & (df_b[data_col].notna())].copy()

            if not target_df.empty:
                # (中略: ヒートマップの描画コードはそのまま維持してください)
                # ... (前回の回答のヒートマップ描画部分をここに入れてください) ...

                # --- 2. 扇形角度分布（イメージ再現） ---
                st.markdown("---")
                st.subheader("📐 打球角度分布（Launch Angle Distribution）")
                
                angle_data = target_df['Angle'].dropna()
                
                if not angle_data.empty:
                    # 10度刻みの集計
                    bins = np.arange(-20, 70, 10)
                    counts, _ = np.histogram(angle_data, bins=bins)
                    pcts = (counts / len(angle_data)) * 100
                    
                    # 極座標グラフの作成
                    fig_polar = plt.figure(figsize=(10, 6))
                    ax_polar = fig_polar.add_subplot(111, polar=True)
                    
                    # 角度をラジアンに変換 (野球の角度0度を極座標の0（右）にする)
                    theta = np.deg2rad([(b + 5) for b in bins[:-1]])
                    width = np.deg2rad(8) # 棒の幅
                    
                    # 棒の描画
                    bars = ax_polar.bar(theta, pcts, width=width, color='darkred', alpha=0.6, edgecolor='black')
                    
                    # 扇形の設定
                    ax_polar.set_thetamin(-30) # 表示範囲
                    ax_polar.set_thetamax(70)
                    ax_polar.set_theta_zero_location('E') # 0度を右側に
                    
                    # ラベルとグリッド
                    ax_polar.set_xlabel("\n打球角度 (°)", fontsize=10)
                    ax_polar.set_yticklabels([f"{int(y)}%" for y in ax_polar.get_yticks()], fontsize=8)
                    
                    # バレルゾーン(25-35度付近)を薄くハイライト
                    ax_polar.fill_between(np.deg2rad([25, 35]), 0, max(pcts)+5, color='orange', alpha=0.2, label='バレル想定')
                    
                    # 各棒の上に％を表示
                    for t, p in zip(theta, pcts):
                        if p > 0:
                            ax_polar.text(t, p + 2, f"{p:.1f}%", ha='center', va='bottom', fontsize=9, fontweight='bold')

                    st.pyplot(fig_polar)
                else:
                    st.info("角度データが不足しています。")
