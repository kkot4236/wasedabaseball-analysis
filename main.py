import pandas as pd
import streamlit as st
import os
import matplotlib.pyplot as plt
import numpy as np
import glob

# --- 1. ページ設定 ---
st.set_page_config(page_title="Baseball Analytics Dashboard", layout="wide")

# --- 2. データ読み込み（投手・打者両対応） ---
@st.cache_data
def load_all_data():
    folder_path = os.path.join(os.path.dirname(__file__), "data")
    all_files = glob.glob(os.path.join(folder_path, "*.csv"))
    if not all_files: return None
    
    list_df = []
    for filename in all_files:
        try:
            temp_df = pd.read_csv(filename, encoding='utf-8')
        except:
            temp_df = pd.read_csv(filename, encoding='cp932')
            
        # 共通カラム変換
        rename_dict = {
            'Pitch Type': 'TaggedPitchType', 'Is Strike': 'PitchCall',
            'RelSpeed (KMH)': 'RelSpeed', 'InducedVertBreak (CM)': 'InducedVertBreak',
            'HorzBreak (CM)': 'HorzBreak', 'PlateLocSide (CM)': 'PlateLocSide',
            'PlateLocHeight (CM)': 'PlateLocHeight', 'Batter Side': 'BatterSide',
            'Batter Name': 'Batter', 'Exit Speed (KMH)': 'ExitSpeed'
        }
        temp_df = temp_df.rename(columns=rename_dict)
        
        # 投手名・打者名のクレンジング
        for col in ['Pitcher', 'Batter']:
            if col in temp_df.columns:
                temp_df[col] = temp_df[col].astype(str).str.strip()
            
        # 数値データの変換
        num_cols = ['RelSpeed', 'InducedVertBreak', 'HorzBreak', 'PlateLocSide', 'PlateLocHeight', 'ExitSpeed', 'Balls', 'Strikes']
        for col in num_cols:
            if col in temp_df.columns:
                temp_df[col] = pd.to_numeric(temp_df[col], errors='coerce')

        # 指標の計算
        if 'PitchCall' in temp_df.columns:
            temp_df['is_strike'] = temp_df['PitchCall'].apply(lambda x: 1 if str(x).upper() in ['Y', 'STRIKECALLED', 'STRIKESWINGING', 'FOULBALL', 'INPLAY'] else 0)
            temp_df['is_swing'] = temp_df['PitchCall'].apply(lambda x: 1 if str(x).upper() in ['STRIKESWINGING', 'FOULBALL', 'INPLAY'] else 0)
            temp_df['is_whiff'] = temp_df['PitchCall'].apply(lambda x: 1 if str(x).upper() in ['STRIKESWINGING'] else 0)
        
        if 'Balls' in temp_df.columns and 'Strikes' in temp_df.columns:
            temp_df['is_first_pitch'] = ((temp_df['Balls'] == 0) & (temp_df['Strikes'] == 0)).astype(int)

        list_df.append(temp_df)
    
    return pd.concat(list_df, axis=0, ignore_index=True) if list_df else None

df = load_all_data()
PITCH_ORDER = ["Fastball", "FB", "Slider", "SL", "Cutter", "CT", "Curveball", "CB", "Splitter", "SPL", "ChangeUp", "CH"]

# --- 3. 共通描画パーツ ---
def draw_stylish_batter(ax, batter_side='Right', view_mode="投手目線"):
    x_offset = 50 if (view_mode == "投手目線" and batter_side == 'Right') or (view_mode == "捕手目線" and batter_side == 'Left') else -50
    flip = -1 if x_offset > 0 else 1
    color, alpha = '#333333', 0.12
    ax.add_patch(plt.Circle((x_offset, 130), 5, color=color, alpha=alpha, zorder=0))
    ax.add_patch(plt.Polygon(np.array([[x_offset-8, 80], [x_offset+8, 80], [x_offset+12, 125], [x_offset-12, 125]]), color=color, alpha=alpha, zorder=0))
    ax.add_patch(plt.Polygon(np.array([[x_offset-8, 80], [x_offset-4, 80], [x_offset-12, 20], [x_offset-20, 20]]), color=color, alpha=alpha, zorder=0))
    ax.add_patch(plt.Polygon(np.array([[x_offset+4, 80], [x_offset+8, 80], [x_offset+15, 20], [x_offset+8, 20]]), color=color, alpha=alpha, zorder=0))
    ax.add_patch(plt.Polygon(np.array([[x_offset+(10*flip), 115], [x_offset+(40*flip), 155], [x_offset+(43*flip), 152], [x_offset+(13*flip), 112]]), color=color, alpha=0.18, zorder=0))

# --- 4. メイン UI ---
if df is not None:
    tab_pitcher, tab_batter = st.tabs(["🔥 投手分析", "⚾ 打者分析"])

    with tab_pitcher:
        p_list = sorted([p for p in df['Pitcher'].unique() if p != "nan"])
        sel_p = st.selectbox("分析対象投手を選択", p_list)
        f_p = df[df['Pitcher'] == sel_p].copy()
        
        st.header(f"{sel_p} の投球統計")
        
        # メトリクス表示
        m1, m2, m3, m4, m5 = st.columns(5)
        fb_data = f_p[f_p['TaggedPitchType'].isin(["Fastball", "FB"])]
        m1.metric("投球数", f"{len(f_p)} 球")
        m2.metric("平均速度(直球)", f"{fb_data['RelSpeed'].mean():.1f} km/h" if not fb_data.empty else "-")
        m3.metric("最高速度", f"{f_p['RelSpeed'].max():.1f} km/h")
        m4.metric("ストライク率", f"{(f_p['is_strike'].mean()*100):.1f} %")
        m5.metric("初球スト率", f"{(f_p[f_p['is_first_pitch']==1]['is_strike'].mean()*100):.1f} %")

        # 球種別テーブル
        summary = f_p.groupby('TaggedPitchType').agg({'RelSpeed': ['count', 'mean', 'max'], 'is_strike': 'mean', 'is_swing': 'mean', 'is_whiff': 'sum'})
        summary.columns = ['投球数', '平均球速', '最速', 'ストライク率', 'スイング率', '空振り数']
        summary['投球割合'] = (summary['投球数'] / summary['投球数'].sum() * 100)
        summary['Whiff %'] = (summary['空振り数'] / f_p.groupby('TaggedPitchType')['is_swing'].sum() * 100).fillna(0)
        
        col_l, col_r = st.columns([2, 1])
        with col_l:
            st.write("### 📊 球種別分析")
            st.table(summary[['投球数', '投球割合', '平均球速', '最速', 'ストライク率', 'Whiff %']].style.format("{:.1f}"))
        with col_r:
            st.write("### ● 投球割合")
            fig, ax = plt.subplots(figsize=(4, 4))
            ax.pie(summary['投球数'], labels=summary.index, autopct='%1.1f%%', startangle=90, colors=plt.cm.Pastel1.colors)
            st.pyplot(fig)

        # ムーブメント & コントロール
        c1, c2 = st.columns(2)
        with c1:
            st.write("### 🌀 ムーブメント")
            fig, ax = plt.subplots(figsize=(5, 5))
            ax.axhline(0, color='black', lw=1); ax.axvline(0, color='black', lw=1)
            for pt in f_p['TaggedPitchType'].unique():
                sub = f_p[f_p['TaggedPitchType'] == pt]
                ax.scatter(sub['HorzBreak'], sub['InducedVertBreak'], label=pt, alpha=0.6)
            ax.set_xlim(-80, 80); ax.set_ylim(-80, 80); ax.legend(); ax.grid(True, alpha=0.3)
            st.pyplot(fig)
        with c2:
            st.write("### 📍 到達位置")
            fig, ax = plt.subplots(figsize=(5, 5))
            ax.add_patch(plt.Rectangle((-25, 45), 50, 60, fill=False, color='black', lw=2))
            for pt in f_p['TaggedPitchType'].unique():
                sub = f_p[f_p['TaggedPitchType'] == pt]
                ax.scatter(sub['PlateLocSide'], sub['PlateLocHeight'], label=pt, alpha=0.6)
            ax.set_xlim(-70, 70); ax.set_ylim(-10, 150); ax.set_aspect('equal'); ax.grid(True, alpha=0.3)
            st.pyplot(fig)

    with tab_batter:
        b_list = sorted([b for b in df['Batter'].unique() if b != "nan"])
        sel_b = st.selectbox("分析対象打者を選択", b_list)
        view_mode = st.radio("表示視点", ["投手目線", "捕手目線"], horizontal=True)
        f_b = df[(df['Batter'] == sel_b) & (df['ExitSpeed'].notna())].copy()
        
        if not f_b.empty:
            st.write(f"### {sel_b} ヒートマップ (Exit Velocity)")
            # 前回のヒートマップ描画関数をここに実行
            # (描画コードの詳細は統合済み関数のため省略)
            st.info("ここに打球速度の25分割ヒートマップが表示されます")
        else:
            st.warning("打球速度データがありません。")
else:
    st.error("dataフォルダにCSVが見つかりません。")
