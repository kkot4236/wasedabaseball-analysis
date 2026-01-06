import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import os
import plotly.express as px
import plotly.graph_objects as go

# ==================================================
# 0. パスワード保護機能
# ==================================================
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = None
    if st.session_state["password_correct"] == True: return True

    def password_entered():
        if st.session_state["password_input"] == "waseda123":
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False

    st.title("🔐 早稲田大学野球部 データ分析ツール Professional")
    st.text_input("パスワードを入力してください", type="password", on_change=password_entered, key="password_input")
    if st.session_state["password_correct"] == False:
        st.error("😕 パスワードが違います。")
    return False

if check_password():
    st.set_page_config(layout="wide", page_title="野球部データ分析ツール Pro")

    # --- 設定 ---
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
        if pitch_type == 'TwoSeamFastBall': return 'p'
        return 'o'

    # --- 集計表関数 ---
    def display_pro_summary_table(df):
        if df.empty: return
        total = len(df)
        # 空振り率などの計算
        df['is_strike'] = df['PitchCall'].isin(['StrikeCalled', 'StrikeSwinging', 'FoulBall', 'InPlayOut', 'Single', 'Double', 'Triple', 'HomeRun'])
        df['is_whiff'] = df['PitchCall'] == 'StrikeSwinging'
        df['is_swing'] = df['PitchCall'].isin(['StrikeSwinging', 'FoulBall', 'InPlayOut', 'Single', 'Double', 'Triple', 'HomeRun'])

        res = df.groupby('TaggedPitchType', observed=True).agg(
            count=('Pitcher', 'count'),
            平均球速=('RelSpeed', 'mean'),
            回転数=('SpinRate', 'mean'),
            縦変化=('InducedVertBreak', 'mean'),
            横変化=('HorzBreak', 'mean'),
            空振り率=('is_whiff', lambda x: (x.sum() / df.loc[x.index, 'is_swing'].sum() * 100) if df.loc[x.index, 'is_swing'].sum() > 0 else 0),
            ストライク率=('is_strike', lambda x: x.mean() * 100)
        ).reset_index()
        
        res['投球割合(球数)'] = res['count'].apply(lambda x: f"{x/total*100:.1f}% ({x})")
        res['TaggedPitchType'] = pd.Categorical(res['TaggedPitchType'], categories=PITCH_LIST, ordered=True)
        res = res.sort_values('TaggedPitchType').dropna(subset=['TaggedPitchType'])
        res = res.rename(columns={'TaggedPitchType': '球種', '空振り率': 'Whiff%', 'ストライク率': 'Strike%'})
        
        st.dataframe(res.style.format(precision=1, subset=['平均球速', '回転数', '縦変化', '横変化', 'Whiff%', 'Strike%']), use_container_width=True, hide_index=True)

    # --- データ読み込み ---
    DATA_DIR = "data"
    all_data = []
    if os.path.exists(DATA_DIR):
        for f in [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]:
            try:
                temp = pd.read_csv(os.path.join(DATA_DIR, f))
                for c in ['PlateLocSide', 'PlateLocHeight', 'RelPosSide', 'RelPosHeight', 'Extension']:
                    if c in temp.columns: temp[c] = temp[c] * 100
                temp['SeasonFile'] = f
                all_data.append(temp)
            except: pass

    if all_data:
        full_df = pd.concat(all_data, ignore_index=True)
        full_df['TaggedPitchType'] = full_df['TaggedPitchType'].replace('FourSeamFastBall', 'Fastball')
        full_df['Date_str'] = pd.to_datetime(full_df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')

        st.sidebar.title("🚀 Pro Menu")
        mode = st.sidebar.radio("モード選択", ["総合レポート", "1人集中分析", "2人比較"])
        
        p1 = st.sidebar.selectbox("投手を選択", sorted(full_df['Pitcher'].unique().astype(str)))
        p1_df = full_df[full_df['Pitcher'].astype(str) == p1]
        p1_throws = p1_df['PitcherThrows'].iloc[0] if 'PitcherThrows' in p1_df.columns else 'Right'

        # フィルタ
        s_dates = st.sidebar.multiselect("日付選択", sorted(p1_df['Date_str'].dropna().unique(), reverse=True))
        target_df1 = p1_df.copy()
        if s_dates: target_df1 = target_df1[target_df1['Date_str'].isin(s_dates)]

        # --- 1人集中分析での球種フィルタ ---
        selected_pitches = PITCH_LIST
        if mode == "1人集中分析":
            st.sidebar.markdown("---")
            st.sidebar.subheader("🎯 球種の絞り込み")
            available_pitches = sorted(target_df1['TaggedPitchType'].unique())
            selected_pitches = st.sidebar.multiselect("表示する球種", available_pitches, default=available_pitches)
        
        filtered_df1 = target_df1[target_df1['TaggedPitchType'].isin(selected_pitches)]

        # --- モード別表示 ---
        if mode == "総合レポート":
            st.header(f"📋 {p1} 投手：総合レポート")
            display_pro_summary_table(target_df1)
            
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("変化量相関")
                fig, ax = plt.subplots(figsize=(5,5))
                for pt in PITCH_LIST:
                    d = target_df1[target_df1['TaggedPitchType']==pt]
                    if not d.empty: ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS[pt], label=pt, alpha=0.5)
                ax.set_xlim(-80,80); ax.set_ylim(-80,80); ax.axvline(0, color='black'); ax.axhline(0, color='black'); ax.set_box_aspect(1); st.pyplot(fig)
            
            with c2:
                st.subheader("球速 vs 縦変化")
                fig, ax = plt.subplots(figsize=(5,5))
                for pt in PITCH_LIST:
                    d = target_df1[target_df1['TaggedPitchType']==pt]
                    if not d.empty: ax.scatter(d['RelSpeed'], d['InducedVertBreak'], color=PITCH_COLORS[pt], alpha=0.5)
                ax.set_xlabel("球速(km/h)"); ax.set_ylabel("縦変化(cm)"); ax.set_box_aspect(1); st.pyplot(fig)

        elif mode == "1人集中分析":
            item = st.sidebar.radio("分析項目", ["変化量", "到達位置", "3Dリリースポイント", "カウント別傾向"])
            st.header(f"👤 {p1}：{item}")

            if item == "3Dリリースポイント":
                st.write("マウスでドラッグして回転、スクロールで拡大できます。")
                fig = px.scatter_3d(
                    filtered_df1, x='RelPosSide', y='Extension', z='RelPosHeight',
                    color='TaggedPitchType', color_discrete_map=PITCH_COLORS,
                    labels={'RelPosSide':'横 [cm]', 'Extension':'Extension [cm]', 'RelPosHeight':'高さ [cm]'},
                    opacity=0.7
                )
                fig.update_layout(scene=dict(aspectmode='cube'))
                st.plotly_chart(fig, use_container_width=True)

            elif item == "変化量":
                fig, ax = plt.subplots(figsize=(6,6))
                for pt in selected_pitches:
                    d = filtered_df1[filtered_df1['TaggedPitchType']==pt]
                    if not d.empty: ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS[pt], marker=get_marker(pt, p1_throws), label=pt, alpha=0.6)
                ax.set_xlim(-80,80); ax.set_ylim(-80,80); ax.axvline(0, color='black'); ax.axhline(0, color='black'); ax.set_box_aspect(1); ax.legend(bbox_to_anchor=(1.05, 1)); st.pyplot(fig)

            elif item == "到達位置":
                c1, c2 = st.columns(2)
                for side, col in [('Right', c1), ('Left', c2)]:
                    with col:
                        st.write(f"対 {side}打者")
                        fig, ax = plt.subplots(figsize=(5,5))
                        ax.add_patch(plt.Rectangle((-25, 45), 50, 60, fill=False, lw=2))
                        d_s = filtered_df1[filtered_df1['BatterSide']==side]
                        for pt in selected_pitches:
                            d_p = d_s[d_s['TaggedPitchType']==pt]
                            if not d_p.empty: ax.scatter(d_p['PlateLocSide'], d_p['PlateLocHeight'], color=PITCH_COLORS[pt], marker=get_marker(pt, p1_throws), alpha=0.6)
                        ax.set_xlim(-100,100); ax.set_ylim(0,200); ax.set_box_aspect(1); st.pyplot(fig)

            elif item == "カウント別傾向":
                st.subheader("カウント別投球割合")
                target_df1['Count'] = target_df1['Balls'].astype(str) + "-" + target_df1['Strikes'].astype(str)
                count_order = ["0-0", "1-0", "0-1", "1-1", "2-0", "0-2", "2-1", "1-2", "3-0", "3-1", "2-2", "3-2"]
                count_data = target_df1.groupby(['Count', 'TaggedPitchType'], observed=True).size().unstack(fill_value=0)
                # 割合に変換
                count_data_pct = count_data.div(count_data.sum(axis=1), axis=0) * 100
                st.bar_chart(count_data_pct)

        elif mode == "2人比較":
            p2 = st.sidebar.selectbox("比較対象を選択", sorted(full_df['Pitcher'].unique().astype(str)), index=1)
            p2_df = full_df[full_df['Pitcher'].astype(str) == p2]
            p2_throws = p2_df['PitcherThrows'].iloc[0] if 'PitcherThrows' in p2_df.columns else 'Right'
            
            st.header(f"⚖️ {p1} vs {p2}")
            col1, col2 = st.columns(2)
            with col1: st.subheader(p1); display_pro_summary_table(target_df1)
            with col2: st.subheader(p2); display_pro_summary_table(p2_df)
            
            comp_item = st.sidebar.radio("比較項目", ["変化量", "3Dリリースポイント"])
            if comp_item == "3Dリリースポイント":
                st.subheader("3Dリリースの比較")
                # 2人を合わせたデータ
                comp_df = pd.concat([target_df1, p2_df])
                fig = px.scatter_3d(comp_df, x='RelPosSide', y='Extension', z='RelPosHeight', color='Pitcher', opacity=0.6)
                st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("dataフォルダにCSVが見つかりません。")
