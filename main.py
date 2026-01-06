import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import os
import plotly.express as px

# --- パスワード保護 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = None
    if st.session_state["password_correct"] == True: return True
    def password_entered():
        if st.session_state["password_input"] == "waseda123":
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False
    st.title("🔐 早稲田大学野球部 データ分析ツール Pro")
    st.text_input("パスワードを入力してください", type="password", on_change=password_entered, key="password_input")
    if st.session_state["password_correct"] == False:
        st.error("😕 パスワードが違います。")
    return False

if check_password():
    st.set_page_config(layout="wide", page_title="野球部データ分析ツール Pro")

    # --- 基本設定 ---
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

    # --- 集計表関数 (画像に基づいた項目) ---
    def display_full_pro_table(df):
        if df.empty: return
        total = len(df)
        df = df.copy()
        df['is_strike'] = df['PitchCall'].isin(['StrikeCalled', 'StrikeSwinging', 'FoulBall', 'InPlayOut', 'Single', 'Double', 'Triple', 'HomeRun'])
        df['is_whiff'] = df['PitchCall'] == 'StrikeSwinging'
        df['is_swing'] = df['PitchCall'].isin(['StrikeSwinging', 'FoulBall', 'InPlayOut', 'Single', 'Double', 'Triple', 'HomeRun'])
        
        agg_map = {
            'RelSpeed': 'mean', 'SpinRate': 'mean', 'InducedVertBreak': 'mean', 
            'HorzBreak': 'mean', 'VertRelAngle': 'mean', 'HorzRelAngle': 'mean'
        }
        # 存在するカラムのみ集計
        actual_agg = {k: v for k, v in agg_map.items() if k in df.columns}
        actual_agg['Pitcher'] = 'count'

        res = df.groupby('TaggedPitchType', observed=True).agg(actual_agg).reset_index()
        res['投球割合(球数)'] = res['Pitcher'].apply(lambda x: f"{x/total*100:.1f}% ({x})")
        
        # 表示用の名前整理
        rename_map = {
            'RelSpeed': '平均(km/h)', 'SpinRate': '回転数', 'InducedVertBreak': '縦変化(cm)', 
            'HorzBreak': '横変化(cm)', 'VertRelAngle': 'アングル(縦)', 'HorzRelAngle': 'アングル(横)'
        }
        res = res.rename(columns=rename_map)
        st.dataframe(res.style.format(precision=1), use_container_width=True, hide_index=True)

    # --- データ読み込み ---
    DATA_DIR = "data"
    all_data = []
    if os.path.exists(DATA_DIR):
        for f in [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]:
            try:
                temp = pd.read_csv(os.path.join(DATA_DIR, f))
                # 単位変換（フィートからセンチ/キロに変換が必要な場合のみ）
                # 今回は画像に合わせて数値として読み込み
                numeric_cols = ['RelSpeed', 'InducedVertBreak', 'HorzBreak', 'RelHeight', 'RelSide', 'Extension', 'VertRelAngle', 'HorzRelAngle', 'SpinRate']
                for c in numeric_cols:
                    if c in temp.columns:
                        temp[c] = pd.to_numeric(temp[c], errors='coerce')
                all_data.append(temp)
            except: pass

    if all_data:
        full_df = pd.concat(all_data, ignore_index=True)
        full_df['TaggedPitchType'] = full_df['TaggedPitchType'].replace('FourSeamFastBall', 'Fastball').fillna('Unknown').astype(str)
        full_df['Date_str'] = pd.to_datetime(full_df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')

        st.sidebar.title("📊 MENU")
        mode = st.sidebar.radio("モード選択", ["総合レポート", "1人集中分析", "2人比較"])
        p1 = st.sidebar.selectbox("投手を選択", sorted(full_df['Pitcher'].unique().astype(str)))
        p1_df = full_df[full_df['Pitcher'].astype(str) == p1].copy()
        p1_throws = p1_df['PitcherThrows'].iloc[0] if 'PitcherThrows' in p1_df.columns else 'Right'

        if mode == "総合レポート":
            st.header(f"📋 {p1} 投手：総合レポート")
            c1, c2 = st.columns(2)
            # 変化量グラフ
            with c1:
                fig, ax = plt.subplots(); 
                for pt in PITCH_LIST:
                    d = p1_df[p1_df['TaggedPitchType']==pt]
                    if not d.empty: ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                ax.axvline(0, color='black', lw=1); ax.axhline(0, color='black', lw=1); ax.set_xlim(-60,60); ax.set_ylim(-60,60); ax.set_title("変化量(cm)"); ax.set_box_aspect(1); st.pyplot(fig)
            # アングルグラフ
            with c2:
                fig, ax = plt.subplots();
                for pt in PITCH_LIST:
                    d = p1_df[p1_df['TaggedPitchType']==pt]
                    if not d.empty: ax.scatter(d['HorzRelAngle'], d['VertRelAngle'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                ax.axvline(0, color='black', lw=1); ax.axhline(0, color='black', lw=1); ax.set_xlim(-6,6); ax.set_ylim(-6,6); ax.set_title("リリースアングル"); ax.set_box_aspect(1); st.pyplot(fig)
            display_full_pro_table(p1_df)

        elif mode == "1人集中分析":
            item = st.sidebar.radio("分析項目", ["変化量詳細", "3Dリリースポイント", "リリース位置の安定度", "球速・回転数の分布"])
            st.header(f"👤 {p1}：{item}")
            
            # リリース位置のカラムを画像に基づいて定義
            h_col, s_col, e_col = 'RelHeight', 'RelSide', 'Extension'

            if item == "3Dリリースポイント":
                if all(c in p1_df.columns for c in [h_col, s_col, e_col]):
                    plot_df = p1_df.dropna(subset=[h_col, s_col, e_col])
                    fig = px.scatter_3d(plot_df, x=s_col, y=e_col, z=h_col, color='TaggedPitchType', color_discrete_map=PITCH_COLORS, labels={s_col:'横位置', e_col:'Extension', h_col:'高さ'})
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.error("リリース位置のデータ(RelHeight/RelSide/Extension)が不足しています。")

            elif item == "リリース位置の安定度":
                if h_col in p1_df.columns and s_col in p1_df.columns:
                    fig, ax = plt.subplots()
                    for pt in p1_df['TaggedPitchType'].unique():
                        d = p1_df[p1_df['TaggedPitchType']==pt]
                        ax.scatter(d[s_col], d[h_col], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                    ax.set_xlabel("横リリース"); ax.set_ylabel("高さリリース"); ax.set_box_aspect(1); ax.legend(); st.pyplot(fig)

            elif item == "球速・回転数の分布":
                c1, c2 = st.columns(2)
                with c1: st.plotly_chart(px.box(p1_df, x='TaggedPitchType', y='RelSpeed', color='TaggedPitchType', color_discrete_map=PITCH_COLORS, title="球速分布"), use_container_width=True)
                with c2: st.plotly_chart(px.box(p1_df, x='TaggedPitchType', y='SpinRate', color='TaggedPitchType', color_discrete_map=PITCH_COLORS, title="回転数分布"), use_container_width=True)
            
            display_full_pro_table(p1_df)

        elif mode == "2人比較":
            p2 = st.sidebar.selectbox("比較相手", sorted(full_df['Pitcher'].unique().astype(str)), index=min(1, len(full_df['Pitcher'].unique())-1))
            c1, c2 = st.columns(2)
            with c1: st.subheader(p1); display_full_pro_table(p1_df)
            with c2: st.subheader(p2); display_full_pro_table(full_df[full_df['Pitcher']==p2])
