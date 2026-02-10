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

    # --- 2. 基本設定・描画関数 ---
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

    def draw_stylish_batter(ax, batter_side='Right', view_mode="投手目線"):
        if view_mode == "投手目線":
            x_offset = 55 if batter_side == 'Right' else -55
            flip = -1 if batter_side == 'Right' else 1
        else:
            x_offset = -55 if batter_side == 'Right' else 55
            flip = 1 if batter_side == 'Right' else -1
            
        color, alpha = '#333333', 0.15
        ax.add_patch(plt.Circle((x_offset, 140), 6, color=color, alpha=alpha, zorder=1))
        ax.add_patch(plt.Polygon(np.array([[x_offset-12, 85], [x_offset+12, 85], [x_offset+15, 135], [x_offset-15, 135]]), color=color, alpha=alpha, zorder=1))
        ax.add_patch(plt.Polygon(np.array([[x_offset-10, 85], [x_offset-2, 85], [x_offset-15, 20], [x_offset-25, 20]]), color=color, alpha=alpha, zorder=1))
        ax.add_patch(plt.Polygon(np.array([[x_offset+2, 85], [x_offset+10, 85], [x_offset+25, 20], [x_offset+15, 20]]), color=color, alpha=alpha, zorder=1))
        ax.add_patch(plt.Polygon(np.array([[x_offset+(15*flip), 125], [x_offset+(40*flip), 170], [x_offset+(48*flip), 167], [x_offset+(18*flip), 122]]), color=color, alpha=0.25, zorder=1))

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
        st.dataframe(res.rename(columns={'TaggedPitchType':'球種','RelSpeed':'平均(km/h)','SpinRate':'回転数','InducedVertBreak':'縦変化','HorzBreak':'横変化'}).style.format(precision=1), use_container_width=True, hide_index=True)

    # --- 3. データ読み込み ---
    @st.cache_data
    def load_data():
        DATA_DIR = "data"
        all_data = []
        if os.path.exists(DATA_DIR):
            for f in [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]:
                try:
                    df = pd.read_csv(os.path.join(DATA_DIR, f))
                    cols = ['RelSpeed', 'InducedVertBreak', 'HorzBreak', 'RelHeight', 'RelSide', 'Extension', 'PlateLocSide', 'PlateLocHeight', 'ExitSpeed', 'Angle', 'Distance', 'Balls', 'Strikes']
                    for c in cols:
                        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
                    # 単位変換
                    for c in ['RelHeight', 'RelSide', 'Extension', 'PlateLocSide', 'PlateLocHeight']:
                        if c in df.columns: df[c] *= 100
                    if 'Distance' in df.columns: df['Distance'] *= 0.3048 # feet to meters
                    df['SeasonFile'] = f
                    all_data.append(df)
                except: pass
        return pd.concat(all_data, ignore_index=True) if all_data else None

    df_full = load_data()

    if df_full is not None:
        df_full['TaggedPitchType'] = df_full['TaggedPitchType'].replace('FourSeamFastBall', 'Fastball').fillna('Unknown').astype(str)
        df_full['Date_str'] = pd.to_datetime(df_full['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
        p_col = 'Pitcher' if 'Pitcher' in df_full.columns else 'Pitcher Name'
        b_col = 'Batter Name' if 'Batter Name' in df_full.columns else 'Batter'

        mode = st.radio("🏠 モード選択", ["🔥 投手分析", "⚾ 打者分析"], horizontal=True, label_visibility="collapsed")

        # --- 5. メインロジック ---
        if mode == "🔥 投手分析":
            st.sidebar.title("🔥 PITCHER MENU")
            p_list = sorted([str(p) for p in df_full[p_col].unique() if pd.notna(p)])
            sel_p = st.sidebar.selectbox("投手を選択", p_list, key="p_sel")
            p_mode = st.sidebar.radio("レポート形式", ["総合レポート", "1人集中分析"], key="p_report_mode")
            
            p_full = df_full[df_full[p_col].astype(str) == sel_p].copy()
            s_files = st.sidebar.multiselect("ファイル絞り込み", sorted(p_full['SeasonFile'].unique()), key="p_file_sel")
            s_dates = st.sidebar.multiselect("日付絞り込み", sorted(p_full['Date_str'].dropna().unique(), reverse=True), key="p_date_sel")
            
            target_p_df = p_full.copy()
            if s_files: target_p_df = target_p_df[target_p_df['SeasonFile'].isin(s_files)]
            if s_dates: target_p_df = target_p_df[target_p_df['Date_str'].isin(s_dates)]
            p_throws = target_p_df['PitcherThrows'].iloc[0] if not target_p_df.empty and 'PitcherThrows' in target_p_df.columns else 'Right'

            st.header(f"📊 {sel_p} 投手：分析結果")
            if p_mode == "総合レポート":
                c1, c2 = st.columns(2)
                with c1:
                    fig, ax = plt.subplots(figsize=(6, 6))
                    for pt in PITCH_LIST:
                        d = target_p_df[target_p_df['TaggedPitchType']==pt]
                        if not d.empty: ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6, marker=get_marker(pt, p_throws))
                    ax.axvline(0, color='black', lw=1); ax.axhline(0, color='black', lw=1); ax.set_xlim(-80,80); ax.set_ylim(-80,80); ax.set_title("変化量(cm)"); st.pyplot(fig)
                with c2:
                    fig, ax = plt.subplots(figsize=(6, 6))
                    for pt in PITCH_LIST:
                        d = target_p_df[target_p_df['TaggedPitchType']==pt]
                        if not d.empty: ax.scatter(d['HorzRelAngle'], d['VertRelAngle'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6, marker=get_marker(pt, p_throws))
                    ax.axvline(0, color='black', lw=1); ax.axhline(0, color='black', lw=1); ax.set_xlim(-6,6); ax.set_ylim(-6,6); ax.set_title("リリース角"); st.pyplot(fig)
                display_full_pro_table(target_p_df)
            elif p_mode == "1人集中分析":
                p_item = st.sidebar.radio("詳細項目", ["変化量詳細", "到達位置", "3Dリリース", "カウント別"], key="p_detail_sel")
                # (投手分析の詳細は前述の通り動作)
                if p_item == "変化量詳細":
                    fig, ax = plt.subplots(figsize=(6, 6))
                    for pt in target_p_df['TaggedPitchType'].unique():
                        d = target_p_df[target_p_df['TaggedPitchType']==pt]
                        ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                    ax.axvline(0); ax.axhline(0); ax.set_xlim(-80,80); ax.set_ylim(-80,80); ax.legend(bbox_to_anchor=(1.05, 1)); st.pyplot(fig)
                display_full_pro_table(target_p_df)

        elif mode == "⚾ 打者分析":
            # --- 打者サイドバー：拡張 ---
            st.sidebar.title("⚾ BATTER MENU")
            b_list = sorted([str(b) for b in df_full[b_col].unique() if pd.notna(b)])
            sel_b = st.sidebar.selectbox("打者を選択", b_list, key="b_sel")
            
            # コース別分析の指標選択を追加
            analysis_target = st.sidebar.radio("分析指標を選択", ["打球速度 (km/h)", "打球角度 (deg)", "飛距離 (m)"], key="b_target")
            view_mode = st.sidebar.radio("表示視点", ["投手目線", "捕手目線"], key="b_view")
            
            b_full = df_full[df_full[b_col] == sel_b].copy()
            st.header(f"🎯 {sel_b} 打者：コース別 {analysis_target}")
            
            if not b_full.empty:
                b_full['PlateLocSide_Plot'] = b_full['PlateLocSide'] * (-1 if view_mode == "捕手目線" else 1)
                b_hand = b_full['BatterSide'].mode()[0] if not b_full['BatterSide'].dropna().empty else 'Right'
                
                # 指標に応じた色・範囲設定
                if analysis_target == "打球速度 (km/h)":
                    target_col, v_min, v_max, cmap = 'ExitSpeed', 100, 165, 'Reds'
                    unit = "km/h"
                elif analysis_target == "打球角度 (deg)":
                    # 角度は10〜30度（ライナー）を濃くする設定
                    target_col, v_min, v_max, cmap = 'Angle', 0, 45, 'viridis'
                    unit = "°"
                else: # 飛距離
                    target_col, v_min, v_max, cmap = 'Distance', 30, 110, 'Blues'
                    unit = "m"

                x_edges = [-36.5, -21.5, -7.17, 7.17, 21.5, 36.5]
                y_edges = [30.0, 45.0, 65.0, 85.0, 105.0, 120.0]

                fig_h, axes_h = plt.subplots(1, 3, figsize=(20, 8), facecolor='white')
                filters_h = [b_full, b_full[b_full['PitcherThrows'] == 'Right'], b_full[b_full['PitcherThrows'] == 'Left']]
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
                            if not zone_data.empty:
                                val = zone_data[target_col].mean()
                                if pd.notna(val):
                                    norm = (val - v_min) / (v_max - v_min)
                                    color = plt.get_cmap(cmap)(np.clip(norm, 0, 1))
                                    ax.add_patch(plt.Rectangle((x_min, y_min), x_max-x_min, y_max-y_min, color=color, alpha=0.8, ec='white', lw=0.5, zorder=2))
                                    # テキスト色の自動調整
                                    txt_c = 'white' if norm > 0.6 and cmap != 'viridis' else 'black'
                                    ax.text((x_min + x_max)/2, (y_min + y_max)/2, f"{val:.1f}{unit}\n$n$={len(zone_data)}", ha='center', va='center', fontweight='bold', fontsize=8, color=txt_c, zorder=3)
                    
                    ax.add_patch(plt.Rectangle((-21.5, 45.0), 43.0, 60.0, fill=False, edgecolor='black', lw=2, zorder=4))
                    ax.set_xlim(-90, 90); ax.set_ylim(10, 180); ax.set_aspect('equal'); ax.axis('off'); ax.set_title(titles_h[i])
                st.pyplot(fig_h)
            else:
                st.warning("データが見つかりません。")

    else:
        st.error("dataフォルダにCSVが見つかりません。")
