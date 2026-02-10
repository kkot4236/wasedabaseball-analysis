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
    st.title("🔐 早稲田大学野球部 データ分析ツール Pro+")
    st.text_input("パスワードを入力してください", type="password", on_change=password_entered, key="password_input")
    if st.session_state["password_correct"] == False:
        st.error("😕 パスワードが違います。")
    return False

if check_password():
    st.set_page_config(layout="wide", page_title="野球部データ分析ツール Pro+")

    # --- 2. 基本設定・定数 ---
    PITCH_LIST = ['Fastball', 'Slider', 'Cutter', 'Curveball', 'Splitter', 'ChangeUp', 'Sinker', 'TwoSeamFastBall']
    PITCH_COLORS = {
        'Fastball': '#FF4B4B', 'Slider': '#1E90FF', 'Cutter': '#FF1493', 
        'Curveball': '#32CD32', 'Splitter': '#40E0D0', 'ChangeUp': '#8A2BE2', 
        'Sinker': '#FFA500', 'TwoSeamFastBall': '#FF8C00'
    }

    def get_marker(pitch_type, throws):
        if pitch_type == 'Fastball': return 'o'
        if pitch_type in ['Slider', 'Cutter']: return '<' if throws == 'Right' else '>'
        if pitch_type == 'Splitter': return 's'
        if pitch_type in ['ChangeUp', 'Sinker']: return 'v'
        if pitch_type == 'Curveball': return '^'
        return 'o'

    # --- 3. 描画用パーツ (打者シルエット) ---
    def draw_stylish_batter(ax, batter_side='Right', view_mode="投手目線"):
        # 視点と打席による立ち位置の決定
        if view_mode == "投手目線":
            x_offset = 50 if batter_side == 'Right' else -50
            flip = -1 if batter_side == 'Right' else 1
        else: # 捕手目線
            x_offset = -50 if batter_side == 'Right' else 50
            flip = 1 if batter_side == 'Right' else -1

        color, alpha = '#333333', 0.12
        ax.add_patch(plt.Circle((x_offset, 130), 5, color=color, alpha=alpha, zorder=0))
        ax.add_patch(plt.Polygon(np.array([[x_offset-8, 80], [x_offset+8, 80], [x_offset+12, 125], [x_offset-12, 125]]), color=color, alpha=alpha, zorder=0))
        ax.add_patch(plt.Polygon(np.array([[x_offset-8, 80], [x_offset-4, 80], [x_offset-12, 20], [x_offset-20, 20]]), color=color, alpha=alpha, zorder=0))
        ax.add_patch(plt.Polygon(np.array([[x_offset+4, 80], [x_offset+8, 80], [x_offset+15, 20], [x_offset+8, 20]]), color=color, alpha=alpha, zorder=0))
        ax.add_patch(plt.Polygon(np.array([[x_offset+(10*flip), 115], [x_offset+(40*flip), 155], [x_offset+(43*flip), 152], [x_offset+(13*flip), 112]]), color=color, alpha=0.18, zorder=0))

    # --- 4. 統計表表示関数 (投手用) ---
    def display_full_pro_table(df):
        if df.empty: return
        total = len(df)
        df = df.copy()
        df['is_strike'] = df['PitchCall'].isin(['StrikeCalled', 'StrikeSwinging', 'FoulBall', 'InPlayOut', 'Single', 'Double', 'Triple', 'HomeRun'])
        df['is_whiff'] = df['PitchCall'] == 'StrikeSwinging'
        df['is_swing'] = df['PitchCall'].isin(['StrikeSwinging', 'FoulBall', 'InPlayOut', 'Single', 'Double', 'Triple', 'HomeRun'])
        
        agg_map = {'RelSpeed': 'mean', 'SpinRate': 'mean', 'InducedVertBreak': 'mean', 'HorzBreak': 'mean'}
        actual_agg = {k: v for k, v in agg_map.items() if k in df.columns}
        actual_agg['Pitcher'] = 'count'
        
        res = df.groupby('TaggedPitchType', observed=True).agg(actual_agg).reset_index()
        whiff_res = df.groupby('TaggedPitchType', observed=True).apply(lambda x: (x['is_whiff'].sum() / x['is_swing'].sum() * 100) if x['is_swing'].sum() > 0 else 0).reset_index(name='Whiff%')
        strike_res = df.groupby('TaggedPitchType', observed=True).apply(lambda x: x['is_strike'].mean() * 100).reset_index(name='Strike%')
        
        res = res.merge(whiff_res, on='TaggedPitchType').merge(strike_res, on='TaggedPitchType')
        res['投球割合'] = res['Pitcher'].apply(lambda x: f"{x/total*100:.1f}% ({x}球)")
        res['TaggedPitchType'] = pd.Categorical(res['TaggedPitchType'], categories=PITCH_LIST, ordered=True)
        res = res.sort_values('TaggedPitchType').dropna(subset=['TaggedPitchType'])
        st.dataframe(res.rename(columns={'TaggedPitchType':'球種','RelSpeed':'平均(km/h)','SpinRate':'回転数','InducedVertBreak':'縦変化','HorzBreak':'横変化','Pitcher':'球数'}).style.format(precision=1), use_container_width=True, hide_index=True)

    # --- 5. データ読み込み ---
    DATA_DIR = "data"
    all_data = []
    if os.path.exists(DATA_DIR):
        csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
        for f in csv_files:
            try:
                try:
                    temp = pd.read_csv(os.path.join(DATA_DIR, f), encoding='utf-8')
                except:
                    temp = pd.read_csv(os.path.join(DATA_DIR, f), encoding='cp932')
                
                num_cols = ['RelSpeed', 'InducedVertBreak', 'HorzBreak', 'RelHeight', 'RelSide', 'Extension', 'VertRelAngle', 'HorzRelAngle', 'SpinRate', 'PlateLocSide', 'PlateLocHeight', 'ExitSpeed']
                for c in num_cols:
                    if c in temp.columns: temp[c] = pd.to_numeric(temp[c], errors='coerce')
                
                # フィートからセンチメートル変換 (既存処理)
                for c in ['RelHeight', 'RelSide', 'Extension', 'PlateLocSide', 'PlateLocHeight']:
                    if c in temp.columns: temp[c] = temp[c] * 100
                
                temp['SeasonFile'] = f
                all_data.append(temp)
            except: pass

    if all_data:
        full_df = pd.concat(all_data, ignore_index=True)
        # 投手名カラムの統一
        p_col = 'Pitcher' if 'Pitcher' in full_df.columns else 'Pitcher Name'
        # 打者名カラムの統一
        b_col = 'Batter Name' if 'Batter Name' in full_df.columns else 'Batter'
        
        full_df['TaggedPitchType'] = full_df['TaggedPitchType'].replace('FourSeamFastBall', 'Fastball').fillna('Unknown').astype(str)
        full_df['Date_str'] = pd.to_datetime(full_df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')

        # --- 6. タブ構成 ---
        tab_p, tab_b = st.tabs(["🔥 投手分析 (Pitcher)", "⚾ 打者分析 (Batter)"])

        # ==========================================
        # 投手分析セクション
        # ==========================================
        with tab_p:
            st.sidebar.title("📊 PITCHER MENU")
            p_mode = st.sidebar.radio("モード選択", ["総合レポート", "1人集中分析", "2人比較"], key="p_mode")
            p_list = sorted([str(p) for p in full_df[p_col].unique() if pd.notna(p)])
            p1 = st.sidebar.selectbox("投手を選択", p_list, key="p1_sel")
            
            p1_full = full_df[full_df[p_col].astype(str) == p1].copy()
            s_files = st.sidebar.multiselect("ファイル選択", sorted(p1_full['SeasonFile'].unique()), key="f1")
            s_dates = st.sidebar.multiselect("日付選択", sorted(p1_full['Date_str'].dropna().unique(), reverse=True), key="d1")
            
            target_df1 = p1_full.copy()
            if s_files: target_df1 = target_df1[target_df1['SeasonFile'].isin(s_files)]
            if s_dates: target_df1 = target_df1[target_df1['Date_str'].isin(s_dates)]
            p1_throws = target_df1['PitcherThrows'].iloc[0] if not target_df1.empty and 'PitcherThrows' in target_df1.columns else 'Right'

            if p_mode == "総合レポート":
                st.header(f"📋 {p1} 投手：総合レポート")
                c1, c2 = st.columns(2)
                with c1:
                    fig, ax = plt.subplots(figsize=(6, 6))
                    for pt in PITCH_LIST:
                        d = target_df1[target_df1['TaggedPitchType']==pt]
                        if not d.empty: ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6, marker=get_marker(pt, p1_throws))
                    ax.axvline(0, color='black', lw=1); ax.axhline(0, color='black', lw=1); ax.set_xlim(-80,80); ax.set_ylim(-80,80)
                    ax.set_title("変化量(cm)"); ax.set_box_aspect(1); st.pyplot(fig)
                with c2:
                    fig, ax = plt.subplots(figsize=(6, 6))
                    for pt in PITCH_LIST:
                        d = target_df1[target_df1['TaggedPitchType']==pt]
                        if not d.empty: ax.scatter(d['HorzRelAngle'], d['VertRelAngle'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6, marker=get_marker(pt, p1_throws))
                    ax.axvline(0, color='black', lw=1); ax.axhline(0, color='black', lw=1); ax.set_xlim(-6,6); ax.set_ylim(-6,6)
                    ax.set_title("リリースアングル"); ax.set_box_aspect(1); st.pyplot(fig)
                display_full_pro_table(target_df1)

            elif p_mode == "1人集中分析":
                p_item = st.sidebar.radio("分析項目", ["変化量詳細", "到達位置", "3Dリリース", "リリース安定度", "分布分析", "カウント別"], key="p_item_radio")
                st.header(f"👤 {p1}：{p_item}")
                if p_item == "変化量詳細":
                    fig, ax = plt.subplots(figsize=(6, 6))
                    for pt in target_df1['TaggedPitchType'].unique():
                        d = target_df1[target_df1['TaggedPitchType']==pt]
                        ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6, marker=get_marker(pt, p1_throws))
                    ax.axvline(0); ax.axhline(0); ax.set_xlim(-80,80); ax.set_ylim(-80,80); ax.legend(bbox_to_anchor=(1.05, 1)); st.pyplot(fig)
                elif p_item == "到達位置":
                    c1, c2 = st.columns(2)
                    for side, col in [('Right', c1), ('Left', c2)]:
                        with col:
                            fig, ax = plt.subplots(figsize=(6, 6)); ax.add_patch(plt.Rectangle((-25, 45), 50, 60, fill=False, lw=2))
                            d_s = target_df1[target_df1['BatterSide']==side]
                            for pt in target_df1['TaggedPitchType'].unique():
                                d_p = d_s[d_s['TaggedPitchType']==pt]
                                if not d_p.empty: ax.scatter(d_p['PlateLocSide'], d_p['PlateLocHeight'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                            ax.set_xlim(-100,100); ax.set_ylim(0,200); ax.set_title(f"対 {side}打者"); st.pyplot(fig)
                elif p_item == "3Dリリース":
                    plot_df = target_df1.dropna(subset=['RelSide', 'Extension', 'RelHeight'])
                    st.plotly_chart(px.scatter_3d(plot_df, x='RelSide', y='Extension', z='RelHeight', color='TaggedPitchType', color_discrete_map=PITCH_COLORS), use_container_width=True)
                elif p_item == "カウント別":
                    target_df1['Count'] = target_df1['Balls'].fillna(0).astype(int).astype(str) + "-" + target_df1['Strikes'].fillna(0).astype(int).astype(str)
                    count_data = target_df1.groupby(['Count', 'TaggedPitchType'], observed=True).size().unstack(fill_value=0)
                    st.bar_chart(count_data.div(count_data.sum(axis=1), axis=0) * 100)
                display_full_pro_table(target_df1)

        # ==========================================
        # 打者分析セクション
        # ==========================================
        with tab_b:
            st.header("⚾ 打者別ヒートマップ分析")
            if b_col in full_df.columns:
                b_list = sorted([str(b) for b in full_df[b_col].unique() if pd.notna(b) and str(b) != "nan"])
                sel_b = st.selectbox("分析対象打者を選択 (Batter Name)", b_list)
                
                view_mode = st.radio("表示視点", ["投手目線", "捕手目線"], horizontal=True, key="b_view")
                b_df = full_df[full_df[b_col] == sel_b].copy()
                
                if not b_df.empty:
                    # 視点による座標変換
                    b_df['PlateLocSide_Plot'] = b_df['PlateLocSide'] * (-1 if view_mode == "捕手目線" else 1)
                    b_hand = b_df['BatterSide'].mode()[0] if 'BatterSide' in b_df.columns and not b_df['BatterSide'].dropna().empty else 'Right'
                    
                    x_edges = [-36.5, -21.5, -7.17, 7.17, 21.5, 36.5]
                    y_edges = [30.0, 45.0, 65.0, 85.0, 105.0, 120.0]
                    V_MIN, V_MAX = 110, 155

                    fig_h, axes_h = plt.subplots(1, 3, figsize=(20, 8), facecolor='white')
                    filters_h = [b_df, b_df[b_df['PitcherThrows'] == 'Right'], b_df[b_df['PitcherThrows'] == 'Left']]
                    titles_h = ['TOTAL', 'VS RIGHT P', 'VS LEFT P']

                    for i, ax in enumerate(axes_h):
                        subset_h = filters_h[i]
                        draw_stylish_batter(ax, b_hand, view_mode)
                        
                        for r in range(5):
                            for c in range(5):
                                x_min, x_max = x_edges[c], x_edges[c+1]
                                y_min, y_max = y_edges[4-r], y_edges[5-r]
                                zone_data = subset_h[(subset_h['PlateLocSide_Plot'] >= x_min) & (subset_h['PlateLocSide_Plot'] < x_max) &
                                                    (subset_h['PlateLocHeight'] >= y_min) & (subset_h['PlateLocHeight'] < y_max)]
                                
                                if not zone_data.empty and 'ExitSpeed' in zone_data.columns:
                                    avg_v = zone_data['ExitSpeed'].mean()
                                    if pd.notna(avg_v):
                                        norm = (avg_v - V_MIN) / (V_MAX - V_MIN)
                                        color = plt.cm.Reds(np.clip(norm, 0, 1))
                                        ax.add_patch(plt.Rectangle((x_min, y_min), x_max-x_min, y_max-y_min, color=color, alpha=0.9, ec='white', lw=0.5))
                                        text_col = 'white' if norm > 0.6 else 'black'
                                        ax.text((x_min + x_max)/2, (y_min + y_max)/2, f"{avg_v:.1f}\n$n$={len(zone_data)}", ha='center', va='center', fontweight='bold', fontsize=8, color=text_col)

                        ax.add_patch(plt.Rectangle((-21.5, 45.0), 43.0, 60.0, fill=False, edgecolor='black', lw=2))
                        ax.set_xlim(-80, 80); ax.set_ylim(10, 160); ax.set_aspect('equal'); ax.axis('off')
                        ax.set_title(titles_h[i], fontsize=12, fontweight='bold')
                    st.pyplot(fig_h)
                else:
                    st.warning("この打者のデータが見つかりません。")
            else:
                st.error("CSVに打者名カラム（Batter Name / Batter）が見つかりません。")

    else:
        st.error("dataフォルダに有効なCSVが見つかりません。")
