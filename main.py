import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import os
import numpy as np
import matplotlib.cm as cm
import plotly.express as px

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
    st.title("東京六大学野球 Trackman Database")
    st.text_input("パスワードを入力してください", type="password", on_change=password_entered, key="password_input")
    if st.session_state["password_correct"] == False:
        st.error(" パスワードが違います。")
    return st.session_state["password_correct"]

if check_password():
    st.set_page_config(layout="wide", page_title="Trackman Database")

    # --- 2. 共通設定・関数 ---
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

    def draw_field(ax):
        r_foul = 120 
        ax.plot([0, -r_foul * np.sin(np.deg2rad(45))], [0, r_foul * np.cos(np.deg2rad(45))], color='black', lw=2, zorder=1)
        ax.plot([0, r_foul * np.sin(np.deg2rad(45))], [0, r_foul * np.cos(np.deg2rad(45))], color='black', lw=2, zorder=1)
        theta = np.linspace(np.deg2rad(135), np.deg2rad(45), 100)
        for dist in [50, 100]:
            ax.plot(dist * np.cos(theta), dist * np.sin(theta), color='gray', lw=0.8, ls='--', alpha=0.5, zorder=1)
            ax.text(0, dist + 2, f"{dist}m", color='gray', fontsize=8, ha='center', alpha=0.7)
        r_fence = 110
        ax.plot(r_fence * np.cos(theta), r_fence * np.sin(theta), color='black', lw=2.5, zorder=2)
        ax.set_aspect('equal'); ax.axis('off')

    def draw_stylish_batter(ax, batter_side='Right', view='投手目線'):
        if view == '投手目線':
            x_offset = 50 if batter_side == 'Right' else -50
            flip = -1 if batter_side == 'Right' else 1
        else:
            x_offset = -50 if batter_side == 'Right' else 50
            flip = 1 if batter_side == 'Right' else -1
        color = '#333333'; alpha = 0.12
        ax.add_patch(plt.Circle((x_offset, 130), 5, color=color, alpha=alpha, zorder=0))
        body = plt.Polygon(np.array([[x_offset-8, 80], [x_offset+8, 80], [x_offset+12, 125], [x_offset-12, 125]]), color=color, alpha=alpha, zorder=0)
        ax.add_patch(body)
        bat = plt.Polygon(np.array([[x_offset+(10*flip), 115], [x_offset+(40*flip), 155], [x_offset+(43*flip), 152], [x_offset+(13*flip), 112]]), color=color, alpha=0.18, zorder=0)
        ax.add_patch(bat)

    def display_pitcher_table(df):
        if df.empty: return
        total = len(df)
        df = df.copy()
        
        # 指標フラグ作成
        swing_calls = ['StrikeSwinging', 'InPlay', 'FoulBallFieldable', 'FoulBallNotFieldable']
        strike_calls = ['StrikeCalled', 'StrikeSwinging', 'InPlay', 'FoulBallFieldable', 'FoulBallNotFieldable']
        df['is_swing'] = df['PitchCall'].isin(swing_calls)
        df['is_whiff'] = df['PitchCall'] == 'StrikeSwinging'
        df['is_strike'] = df['PitchCall'].isin(strike_calls)
        
        # 集計
        agg_map = {'RelSpeed': ['mean', 'max'], 'SpinRate': 'mean', 'InducedVertBreak': 'mean', 'HorzBreak': 'mean'}
        res = df.groupby('TaggedPitchType', observed=True).agg({k: v for k, v in agg_map.items() if k in df.columns})
        res.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in res.columns.values]
        res = res.reset_index()

        stats_df = df.groupby('TaggedPitchType', observed=True).agg({
            'is_whiff': 'sum', 'is_swing': 'sum', 'is_strike': 'sum', 'Pitcher': 'count'
        }).reset_index()

        stats_df['Whiff%'] = (stats_df['is_whiff'] / stats_df['is_swing'] * 100).fillna(0)
        stats_df['Strike%'] = (stats_df['is_strike'] / stats_df['Pitcher'] * 100).fillna(0)
        stats_df['割合'] = stats_df['Pitcher'].apply(lambda x: f"{x/total*100:.1f}% ({x})")

        # 結合と整形
        res = res.merge(stats_df[['TaggedPitchType', 'Whiff%', 'Strike%', '割合']], on='TaggedPitchType')
        res['TaggedPitchType'] = pd.Categorical(res['TaggedPitchType'], categories=PITCH_LIST, ordered=True)
        res = res.sort_values('TaggedPitchType').dropna(subset=['TaggedPitchType'])
        
        # 表示項目のリネームと選択
        final_df = res.rename(columns={
            'TaggedPitchType': '球種', 
            'RelSpeed_mean': '平均(km/h)', 
            'RelSpeed_max': '最高(km/h)', 
            'SpinRate_mean': '回転数', 
            'InducedVertBreak_mean': '縦変化', 
            'HorzBreak_mean': '横変化'
        })
        
        # Pitcher_countを含まない列のみを表示
        show_cols = ['球種', '平均(km/h)', '最高(km/h)', '回転数', '縦変化', '横変化', 'Whiff%', 'Strike%', '割合']
        actual_cols = [c for c in show_cols if c in final_df.columns]
        
        st.dataframe(final_df[actual_cols].style.format(precision=1), use_container_width=True, hide_index=True)

    def render_risk_management_plots(f_data):
        def classify_result(row):
            res, call, hit = str(row.get('PlayResult','')).lower(), str(row.get('PitchCall','')).lower(), str(row.get('TaggedHitType','')).lower()
            if 'home' in res: return '本塁打'
            if 'walk' in res or 'hitby' in res: return '四死球'
            if 'strikeout' in res or 'strikeout' in call or 'popup' in hit or 'swinging' in call: return '完全アウト(内野フライ+三振)'
            if 'ground' in hit: return 'ゴロ'
            if 'fly' in hit or 'line' in hit: return '外野フライ・ライナー'
            return None

        f_risk = f_data.copy()
        f_risk['ResultCategory'] = f_risk.apply(classify_result, axis=1)
        f_risk = f_risk.dropna(subset=['ResultCategory'])
        if f_risk.empty: return st.info("分析用の打球データがありません。")

        cat_order = ['完全アウト(内野フライ+三振)', 'ゴロ', '外野フライ・ライナー', '四死球', '本塁打']
        color_map = {'完全アウト(内野フライ+三振)': '#87CEEB', 'ゴロ': '#9ACD32', '外野フライ・ライナー': '#F0E68C', '四死球': '#FFB444', '本塁打': '#F08080'}

        st.write("##### 左右別")
        side_data = []
        for l, m in [('全体合計', [True]*len(f_risk)), ('対右', f_risk['BatterSide']=='Right'), ('対左', f_risk['BatterSide']=='Left')]:
            sub = f_risk[m]
            if not sub.empty:
                c = sub.groupby('ResultCategory').size().reset_index(name='count')
                c['対象'], c['total'] = l, len(sub)
                side_data.append(c)
        if side_data:
            df_s = pd.concat(side_data)
            df_s['割合(%)'] = (df_s['count'] / df_s['total']) * 100
            st.plotly_chart(px.bar(df_s, y='対象', x='割合(%)', color='ResultCategory', orientation='h', category_orders={'対象':['対左','対右','全体合計'],'ResultCategory':cat_order}, color_discrete_map=color_map, barmode='stack', height=250).update_layout(showlegend=False, margin=dict(l=0,r=0,t=20,b=20)), use_container_width=True)

        st.write("##### 球種別")
        p_t = f_risk.groupby('TaggedPitchType').size().reset_index(name='total')
        p_c = f_risk.groupby(['TaggedPitchType', 'ResultCategory']).size().reset_index(name='count')
        df_p = pd.merge(p_c, p_t, on='TaggedPitchType')
        df_p['割合(%)'] = (df_p['count'] / df_p['total']) * 100
        st.plotly_chart(px.bar(df_p, y='TaggedPitchType', x='割合(%)', color='ResultCategory', orientation='h', category_orders={'TaggedPitchType':PITCH_LIST[::-1],'ResultCategory':cat_order}, color_discrete_map=color_map, barmode='stack', height=350).update_layout(margin=dict(l=0,r=0,t=20,b=80), legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center", title=None)), use_container_width=True)

    @st.cache_data
    def load_all_data(data_dir):
        all_data = []
        if os.path.exists(data_dir):
            for f in [f for f in os.listdir(data_dir) if f.endswith('.csv')]:
                try:
                    temp = pd.read_csv(os.path.join(data_dir, f))
                    num_cols = ['RelSpeed', 'InducedVertBreak', 'HorzBreak', 'RelHeight', 'RelSide', 'Extension', 'VertRelAngle', 'HorzRelAngle', 'SpinRate', 'PlateLocSide', 'PlateLocHeight', 'ExitSpeed', 'Angle', 'Distance', 'Bearing', 'Balls', 'Strikes']
                    for c in num_cols:
                        if c in temp.columns: temp[c] = pd.to_numeric(temp[c], errors='coerce')
                    if 'PlateLocSide' in temp.columns: temp['PlateLocSide_cm'] = temp['PlateLocSide'] * 100
                    if 'PlateLocHeight' in temp.columns: temp['PlateLocHeight_cm'] = temp['PlateLocHeight'] * 100
                    temp['SeasonFile'] = f
                    all_data.append(temp)
                except: pass
        return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

    DATA_DIR = "data"
    full_df = load_all_data(DATA_DIR)

    if not full_df.empty:
        full_df['TaggedPitchType'] = full_df['TaggedPitchType'].replace('FourSeamFastBall', 'Fastball').fillna('Unknown')
        full_df['Date_str'] = pd.to_datetime(full_df['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
        
        st.sidebar.title("● MENU")
        mode = st.sidebar.radio("分析モード", ["投手分析", "打者分析"])

        if mode == "投手分析":
            st.sidebar.subheader("◯ 投手設定")
            p_opts = ["(全員)"] + sorted(full_df['Pitcher'].dropna().unique().astype(str))
            p1_n = st.sidebar.selectbox("投手を選択", p_opts)
            p1_df = full_df.copy() if p1_n == "(全員)" else full_df[full_df['Pitcher'].astype(str) == p1_n].copy()
            
            s_files = st.sidebar.multiselect("ファイル選択", sorted(p1_df['SeasonFile'].unique()))
            s_dates = st.sidebar.multiselect("日付選択", sorted(p1_df['Date_str'].dropna().unique(), reverse=True))
            t_df = p1_df.copy()
            if s_files: t_df = t_df[t_df['SeasonFile'].isin(s_files)]
            if s_dates: t_df = t_df[t_df['Date_str'].isin(s_dates)]
            
            sub_m = st.sidebar.radio("投手分析メニュー", ["総合レポート", "集中分析", "2人比較"])

            if sub_m == "総合レポート":
                st.header(f"◎ {p1_n} 総合レポート")
                c1, c2 = st.columns(2)
                p_thr = t_df['PitcherThrows'].mode()[0] if not t_df.empty else 'Right'
                with c1:
                    fig, ax = plt.subplots(figsize=(6,6))
                    for pt in PITCH_LIST:
                        d = t_df[t_df['TaggedPitchType']==pt]
                        if not d.empty: ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6, marker=get_marker(pt, p_thr))
                    ax.axvline(0, color='black', lw=1); ax.axhline(0, color='black', lw=1); ax.set_xlim(-80,80); ax.set_ylim(-80,80); ax.set_title("変化量(cm)"); st.pyplot(fig)
                with c2:
                    fig, ax = plt.subplots(figsize=(6,6))
                    for pt in PITCH_LIST:
                        d = t_df[t_df['TaggedPitchType']==pt]
                        if not d.empty: ax.scatter(d['HorzRelAngle'], d['VertRelAngle'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                    ax.axvline(0); ax.axhline(0); ax.set_xlim(-6,6); ax.set_ylim(-6,6); ax.set_title("リリースアングル"); st.pyplot(fig)
                display_pitcher_table(t_df)

            else:
                item = st.sidebar.radio("分析項目", ["変化量詳細", "到達位置", "リスク管理(打球結果)", "球速・回転数", "3Dリリース", "リリース安定度", "球速vs変化量", "カウント別"])
                if sub_m == "集中分析":
                    st.header(f"◎ {p1_n} 集中分析: {item}")
                    if item == "変化量詳細":
                        fig, ax = plt.subplots(figsize=(6,6))
                        for pt in PITCH_LIST:
                            d = t_df[t_df['TaggedPitchType']==pt]
                            if not d.empty: ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), alpha=0.6)
                        ax.axvline(0); ax.axhline(0); ax.set_xlim(-80,80); ax.set_ylim(-80,80); st.pyplot(fig)
                    elif item == "到達位置":
                        c1, c2 = st.columns(2)
                        for s, col in [('Right', c1), ('Left', c2)]:
                            with col:
                                fig, ax = plt.subplots(figsize=(6,6)); ax.add_patch(plt.Rectangle((-21.5, 45), 43, 60, fill=False, lw=2))
                                sub = t_df[t_df['BatterSide']==s]
                                for pt in PITCH_LIST:
                                    d_p = sub[sub['TaggedPitchType']==pt]
                                    if not d_p.empty: ax.scatter(d_p['PlateLocSide_cm'], d_p['PlateLocHeight_cm'], color=PITCH_COLORS.get(pt,'gray'), alpha=0.5)
                                ax.set_xlim(-80,80); ax.set_ylim(0,180); ax.set_title(f"対 {s}"); st.pyplot(fig)
                    elif item == "リスク管理(打球結果)": render_risk_management_plots(t_df)
                    elif item == "球速・回転数":
                        st.plotly_chart(px.box(t_df, x="TaggedPitchType", y="RelSpeed", color="TaggedPitchType", color_discrete_map=PITCH_COLORS), use_container_width=True)
                    elif item == "3Dリリース":
                        st.plotly_chart(px.scatter_3d(t_df.dropna(subset=['RelSide','Extension','RelHeight']), x='RelSide', y='Extension', z='RelHeight', color='TaggedPitchType', color_discrete_map=PITCH_COLORS), use_container_width=True)
                    display_pitcher_table(t_df)

                elif sub_m == "2人比較":
                    p2_n = st.sidebar.selectbox("比較投手", sorted(full_df['Pitcher'].dropna().unique().astype(str)), index=1 if len(full_df['Pitcher'].unique())>1 else 0)
                    p2_df = full_df[full_df['Pitcher'].astype(str) == p2_n].copy()
                    st.header(f"◎ 比較: {p1_n} vs {p2_n} 【{item}】")
                    c1, c2 = st.columns(2)
                    for d, col, name in [(t_df, c1, p1_n), (p2_df, c2, p2_n)]:
                        with col:
                            st.subheader(name)
                            if item == "変化量詳細":
                                fig, ax = plt.subplots(figsize=(6,6))
                                for pt in PITCH_LIST:
                                    sub = d[d['TaggedPitchType']==pt]
                                    if not sub.empty: ax.scatter(sub['HorzBreak'], sub['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), alpha=0.6)
                                ax.axvline(0); ax.axhline(0); ax.set_xlim(-80,80); ax.set_ylim(-80,80); st.pyplot(fig)
                            elif item == "到達位置":
                                fig, ax = plt.subplots(figsize=(6,6)); ax.add_patch(plt.Rectangle((-21.5, 45), 43, 60, fill=False, lw=2))
                                for pt in PITCH_LIST:
                                    sub = d[d['TaggedPitchType']==pt]
                                    if not sub.empty: ax.scatter(sub['PlateLocSide_cm'], sub['PlateLocHeight_cm'], color=PITCH_COLORS.get(pt,'gray'), alpha=0.5)
                                ax.set_xlim(-80,80); ax.set_ylim(0,180); st.pyplot(fig)
                            elif item == "リスク管理(打球結果)": render_risk_management_plots(d)
                            elif item == "球速・回転数": st.plotly_chart(px.box(d, x="TaggedPitchType", y="RelSpeed", color="TaggedPitchType", color_discrete_map=PITCH_COLORS), use_container_width=True)
                            display_pitcher_table(d)

        elif mode == "打者分析":
            st.sidebar.subheader("◯ 打者設定")
            b_col = 'Batter' if 'Batter' in full_df.columns else 'Batter Name'
            sel_b = st.sidebar.selectbox("打者を選択", sorted(full_df[b_col].dropna().unique().astype(str)))
            b_df = full_df[full_df[b_col].astype(str) == sel_b].copy()
            s_f = st.sidebar.multiselect("ファイル選択", sorted(b_df['SeasonFile'].unique()), key="bf")
            s_d = st.sidebar.multiselect("日付選択", sorted(b_df['Date_str'].dropna().unique(), reverse=True), key="bd")
            target_b = b_df.copy()
            if s_f: target_b = target_b[target_b['SeasonFile'].isin(s_f)]
            if s_d: target_b = target_b[target_b['Date_str'].isin(s_d)]
            
            v_view = st.sidebar.radio("表示視点", ["投手目線", "捕手目線"])
            t_col = st.sidebar.selectbox("コース別表示項目", ["打球速度", "打球角度", "飛距離"])
            a_metric = st.sidebar.selectbox("角度グラフの指標", ["打率", "平均飛距離", "平均打球速度"])
            
            st.title(f"◎ {sel_b} 分析レポート")
            if not target_b.empty:
                col_m = {"打球速度": "ExitSpeed", "打球角度": "Angle", "飛距離": "Distance"}
                unit_m = {"打球速度": "km/h", "打球角度": "°", "飛距離": "m"}
                norm_m = {"打球速度": (110, 155), "打球角度": (0, 30), "飛距離": (0, 100)}
                d_col, unit, (v_min, v_max) = col_m[t_col], unit_m[t_col], norm_m[t_col]
                hand = target_b['BatterSide'].mode()[0] if 'BatterSide' in target_b.columns else 'Right'
                x_edges = [-36.5, -21.5, -7.17, 7.17, 21.5, 36.5]
                y_edges = [30.0, 45.0, 65.0, 85.0, 105.0, 120.0]
                
                c1, c2, c3 = st.columns(3)
                filters = [target_b, target_b[target_b['PitcherThrows'].str.startswith(('R','r'), na=False)], target_b[target_b['PitcherThrows'].str.startswith(('L','l'), na=False)]]
                titles = ['TOTAL', 'VS RIGHT P', 'VS LEFT P']
                for i, col_ax in enumerate([c1, c2, c3]):
                    subset = filters[i]
                    fig, ax = plt.subplots(figsize=(7, 9))
                    draw_stylish_batter(ax, batter_side=hand, view=v_view)
                    for r in range(5):
                        for c in range(5):
                            x_min, x_max = x_edges[c], x_edges[c+1]
                            y_min, y_max = y_edges[4-r], y_edges[5-r]
                            side_mod = -1 if v_view == "捕手目線" else 1
                            mask = (subset['PlateLocSide_cm'] * side_mod >= x_min) & (subset['PlateLocSide_cm'] * side_mod < x_max) & (subset['PlateLocHeight_cm'] >= y_min) & (subset['PlateLocHeight_cm'] < y_max)
                            z_data = subset[mask]
                            if not z_data.empty:
                                val = z_data[d_col].mean()
                                if not np.isnan(val):
                                    norm_v = (val - v_min) / (v_max - v_min)
                                    ax.add_patch(plt.Rectangle((x_min, y_min), x_max-x_min, y_max-y_min, color=cm.Reds(np.clip(norm_v,0,1)), alpha=0.9, ec='white', lw=0.5, zorder=5))
                                    ax.text((x_min+x_max)/2, (y_min+y_max)/2, f"{val:.1f}{unit}\nn={len(z_data)}", ha='center', va='center', fontweight='bold', fontsize=8, color='white' if norm_v > 0.6 else 'black', zorder=10)
                    ax.add_patch(plt.Rectangle((-21.5, 45.0), 43.0, 60.0, fill=False, ec='black', lw=2.5, zorder=15))
                    ax.set_xlim(-75, 75); ax.set_ylim(15, 165); ax.axis('off'); ax.set_title(titles[i]); col_ax.pyplot(fig)
                
                st.markdown("---")
                low1, low2 = st.columns(2)
                res_col, hit_k = ('PlayResult' if 'PlayResult' in target_b.columns else 'Result'), ['Single', 'Double', 'Triple', 'HomeRun']
                with low1:
                    st.subheader(f"▶︎ 角度別 {a_metric}")
                    bins = np.arange(-20, 71, 10); theta = np.deg2rad(bins[:-1] + 5); vals = []
                    for b_idx in range(len(bins)-1):
                        d = target_b[(target_b['Angle'] >= bins[b_idx]) & (target_b['Angle'] < bins[b_idx+1])]
                        if len(d) > 0:
                            if a_metric == "打率": v = d[res_col].isin(hit_k).sum() / len(d)
                            elif a_metric == "平均飛距離": v = d['Distance'].mean()
                            else: v = d['ExitSpeed'].mean()
                        else: v = 0
                        vals.append(v if not np.isnan(v) else 0)
                    fig_p, ax_p = plt.subplots(figsize=(6, 6), subplot_kw={'projection': 'polar'})
                    ax_p.bar(theta, vals, width=np.deg2rad(9.5), color='darkred', alpha=0.7); ax_p.set_thetamin(-25); ax_p.set_thetamax(75); ax_p.set_theta_zero_location('E'); st.pyplot(fig_p)
                with low2:
                    st.subheader("▶︎ 打球分布")
                    fig_s, ax_s = plt.subplots(figsize=(6, 6)); draw_field(ax_s)
                    if 'Bearing' in target_b.columns and 'Distance' in target_b.columns:
                        for c, l, m in [('gray','凡打',~target_b[res_col].isin(hit_k)), ('red','安打',target_b[res_col].isin(['Single','Double','Triple'])), ('gold','本塁打',target_b[res_col]=='HomeRun')]:
                            sub = target_b[m]
                            rx, ry = sub['Distance'] * np.sin(np.deg2rad(sub['Bearing'])), sub['Distance'] * np.cos(np.deg2rad(sub['Bearing']))
                            ax_s.scatter(rx, ry, color=c, label=l, alpha=0.6, s=100 if l=='本塁打' else 40, marker='*' if l=='本塁打' else 'o')
                        ax_s.legend(); st.pyplot(fig_s)
    else: st.error("CSVデータが見つかりません。")
