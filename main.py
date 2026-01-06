import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import os
import plotly.express as px

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
        if pitch_type == 'TwoSeamFastBall': return 'p'
        return 'o'

    # --- 集計表関数 ---
    def display_full_pro_table(df):
        if df.empty: return
        total = len(df)
        df = df.copy()
        df['is_strike'] = df['PitchCall'].isin(['StrikeCalled', 'StrikeSwinging', 'FoulBall', 'InPlayOut', 'Single', 'Double', 'Triple', 'HomeRun'])
        df['is_whiff'] = df['PitchCall'] == 'StrikeSwinging'
        df['is_swing'] = df['PitchCall'].isin(['StrikeSwinging', 'FoulBall', 'InPlayOut', 'Single', 'Double', 'Triple', 'HomeRun'])

        res = df.groupby('TaggedPitchType', observed=True).agg(
            count=('Pitcher', 'count'),
            平均球速=('RelSpeed', 'mean'),
            最高球速=('RelSpeed', 'max'),
            回転数=('SpinRate', 'mean'),
            縦変化=('InducedVertBreak', 'mean'),
            横変化=('HorzBreak', 'mean'),
            アングル縦=('VertRelAngle', 'mean'),
            アングル横=('HorzRelAngle', 'mean'),
            空振り率=('is_whiff', lambda x: (x.sum() / df.loc[x.index, 'is_swing'].sum() * 100) if df.loc[x.index, 'is_swing'].sum() > 0 else 0),
            ストライク率=('is_strike', lambda x: x.mean() * 100)
        ).reset_index()
        
        res['投球割合(球数)'] = res['count'].apply(lambda x: f"{x/total*100:.1f}% ({x})")
        res['TaggedPitchType'] = pd.Categorical(res['TaggedPitchType'], categories=PITCH_LIST, ordered=True)
        res = res.sort_values('TaggedPitchType').dropna(subset=['TaggedPitchType'])
        
        res = res[['TaggedPitchType', '投球割合(球数)', '平均球速', '最高球速', '回転数', '縦変化', '横変化', 'アングル縦', 'アングル横', '空振り率', 'ストライク率']]
        res = res.rename(columns={
            'TaggedPitchType': '球種', '平均球速': '平均(km/h)', '最高球速': '最高(km/h)',
            '縦変化': '縦変化(cm)', '横変化': '横変化(cm)', 'アングル縦': 'アングル縦', 'アングル横': 'アングル横',
            '空振り率': 'Whiff%', 'ストライク率': 'Strike%'
        })
        st.dataframe(res.style.format(precision=1, subset=['平均(km/h)', '最高(km/h)', '回転数', '縦変化(cm)', '横変化(cm)', 'アングル縦', 'アングル横', 'Whiff%', 'Strike%']), use_container_width=True, hide_index=True)

    # --- 共通グラフ関数（正方形） ---
    def get_square_fig(df, mode_name, title_text, throws, selected_pitches=PITCH_LIST):
        fig, ax = plt.subplots(figsize=(6, 5))
        for pt in selected_pitches:
            d = df[df['TaggedPitchType'] == pt]
            if d.empty: continue
            marker = get_marker(pt, throws)
            if mode_name == "変化量":
                ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS[pt], marker=marker, label=pt, alpha=0.6)
                ax.set_xlim(-80, 80); ax.set_ylim(-80, 80)
            elif mode_name == "リリースアングル":
                ax.scatter(d['HorzRelAngle'], d['VertRelAngle'], color=PITCH_COLORS[pt], marker=marker, label=pt, alpha=0.6)
                ax.set_xlim(-6, 6); ax.set_ylim(-6, 6)
        ax.axvline(0, color='black', lw=1); ax.axhline(0, color='black', lw=1)
        ax.set_box_aspect(1); ax.set_title(title_text, fontweight='bold'); ax.grid(True, alpha=0.3)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
        return fig

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

        st.sidebar.title("📊 MENU")
        mode = st.sidebar.radio("モード選択", ["総合レポート", "1人集中分析", "2人比較"])
        
        p1 = st.sidebar.selectbox("投手を選択", sorted(full_df['Pitcher'].unique().astype(str)))
        p1_df = full_df[full_df['Pitcher'].astype(str) == p1]
        p1_throws = p1_df['PitcherThrows'].iloc[0] if 'PitcherThrows' in p1_df.columns else 'Right'

        s_dates = st.sidebar.multiselect("日付選択", sorted(p1_df['Date_str'].dropna().unique(), reverse=True))
        target_df1 = p1_df.copy()
        if s_dates: target_df1 = target_df1[target_df1['Date_str'].isin(s_dates)]

        # --- 1. 総合レポート (以前の形式を維持) ---
        if mode == "総合レポート":
            st.header(f"📋 {p1} 投手：総合レポート")
            c1, c2 = st.columns(2)
            with c1: st.pyplot(get_square_fig(target_df1, "変化量", "変化量 [cm]", p1_throws))
            with c2: st.pyplot(get_square_fig(target_df1, "リリースアングル", "リリースアングル [度]", p1_throws))
            st.subheader("📊 総合集計スタッツ")
            display_full_pro_table(target_df1)

        # --- 2. 1人集中分析 (新機能を大幅追加) ---
        elif mode == "1人集中分析":
            st.sidebar.markdown("---")
            available_pitches = sorted(target_df1['TaggedPitchType'].unique())
            selected_pitches = st.sidebar.multiselect("表示する球種", available_pitches, default=available_pitches)
            filtered_df1 = target_df1[target_df1['TaggedPitchType'].isin(selected_pitches)]

            item = st.sidebar.radio("分析項目", [
                "変化量詳細", 
                "到達位置", 
                "3Dリリースポイント", 
                "リリース位置の安定度", 
                "球速・回転数の分布",
                "球速 vs 変化量相関",
                "カウント別傾向"
            ])
            st.header(f"👤 {p1}：{item}")

            if item == "変化量詳細":
                st.pyplot(get_square_fig(filtered_df1, "変化量", "変化量分布", p1_throws, selected_pitches))

            elif item == "到達位置":
                c1, c2 = st.columns(2)
                for side, col in [('Right', c1), ('Left', c2)]:
                    with col:
                        fig, ax = plt.subplots(figsize=(6, 5)); ax.add_patch(plt.Rectangle((-25, 45), 50, 60, fill=False, lw=2))
                        d_s = filtered_df1[filtered_df1['BatterSide']==side]
                        for pt in selected_pitches:
                            d_p = d_s[d_s['TaggedPitchType']==pt]
                            if not d_p.empty: ax.scatter(d_p['PlateLocSide'], d_p['PlateLocHeight'], color=PITCH_COLORS[pt], marker=get_marker(pt, p1_throws), label=pt, alpha=0.6)
                        ax.set_xlim(-100,100); ax.set_ylim(0,200); ax.set_box_aspect(1); ax.set_title(f"対 {side}打者"); ax.legend(bbox_to_anchor=(1.05, 1)); st.pyplot(fig)

            elif item == "3Dリリースポイント":
                fig = px.scatter_3d(filtered_df1, x='RelPosSide', y='Extension', z='RelPosHeight', color='TaggedPitchType', color_discrete_map=PITCH_COLORS, opacity=0.7)
                st.plotly_chart(fig, use_container_width=True)

            elif item == "リリース位置の安定度":
                fig, ax = plt.subplots(figsize=(6, 6))
                for pt in selected_pitches:
                    d = filtered_df1[filtered_df1['TaggedPitchType'] == pt]
                    if not d.empty: ax.scatter(d['RelPosSide'], d['RelPosHeight'], color=PITCH_COLORS[pt], label=pt, alpha=0.6, marker=get_marker(pt, p1_throws))
                ax.set_xlabel("横リリース [cm]"); ax.set_ylabel("高さリリース [cm]"); ax.set_box_aspect(1); ax.grid(True, alpha=0.3); ax.legend(bbox_to_anchor=(1.05, 1))
                st.pyplot(fig)

            elif item == "球速・回転数の分布":
                c1, c2 = st.columns(2)
                with c1: st.plotly_chart(px.box(filtered_df1, x="TaggedPitchType", y="RelSpeed", color="TaggedPitchType", color_discrete_map=PITCH_COLORS, title="球速のバラつき"), use_container_width=True)
                with c2: st.plotly_chart(px.box(filtered_df1, x="TaggedPitchType", y="SpinRate", color="TaggedPitchType", color_discrete_map=PITCH_COLORS, title="回転数のバラつき"), use_container_width=True)

            elif item == "球速 vs 変化量相関":
                fig = px.scatter(filtered_df1, x="RelSpeed", y="InducedVertBreak", color="TaggedPitchType", color_discrete_map=PITCH_COLORS, hover_data=['Date'], title="球速と縦変化の関係")
                st.plotly_chart(fig, use_container_width=True)

            elif item == "カウント別傾向":
                target_df1['Count'] = target_df1['Balls'].astype(str) + "-" + target_df1['Strikes'].astype(str)
                count_data = target_df1.groupby(['Count', 'TaggedPitchType'], observed=True).size().unstack(fill_value=0)
                st.bar_chart(count_data.div(count_data.sum(axis=1), axis=0) * 100)
            
            st.subheader("📊 詳細スタッツ")
            display_full_pro_table(filtered_df1)

        # --- 3. 2人比較 ---
        elif mode == "2人比較":
            p2 = st.sidebar.selectbox("比較対象を選択", sorted(full_df['Pitcher'].unique().astype(str)), index=1)
            p2_df = full_df[full_df['Pitcher'].astype(str) == p2]
            st.header(f"⚖️ {p1} vs {p2}")
            col1, col2 = st.columns(2)
            with col1: st.subheader(p1); display_full_pro_table(target_df1)
            with col2: st.subheader(p2); display_full_pro_table(p2_df)
    else:
        st.warning("dataフォルダにCSVが見つかりません。")
