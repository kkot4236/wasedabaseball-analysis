# --- B. 扇形角度分布（半径 = 打率 AVG 版） ---
st.markdown("---")
st.subheader("📐 打球角度別 打率分布（Launch Angle vs AVG）")

# ヒットと判定する結果を定義（CSVのPlayResultカラムの内容に合わせて調整してください）
hit_keywords = ['Single', 'Double', 'Triple', 'HomeRun']

# 必要なデータ（角度と結果）を抽出
angle_df = target_df[['Angle', 'PlayResult']].dropna()

if not angle_df.empty:
    bins = np.arange(-20, 71, 10)
    labels = bins[:-1] + 5  # 各ビンの中心点
    
    # 角度ごとにグループ化して打率を計算
    angle_df['AngleBin'] = pd.cut(angle_df['Angle'], bins=bins)
    
    avg_list = []
    n_list = []
    
    for b in pd.interval_range(start=-20, end=60, freq=10):
        bin_data = angle_df[angle_df['AngleBin'] == b]
        at_bats = len(bin_data)
        if at_bats > 0:
            hits = bin_data['PlayResult'].isin(hit_keywords).sum()
            avg = hits / at_bats
        else:
            avg = 0
        avg_list.append(avg)
        n_list.append(at_bats)

    # グラフ描画
    fig_polar = plt.figure(figsize=(10, 6))
    ax_polar = fig_polar.add_subplot(111, polar=True)
    
    theta = np.deg2rad(labels)
    width = np.deg2rad(9.5)
    
    # 半径を「打率(avg)」に設定
    bars = ax_polar.bar(theta, avg_list, width=width, color='darkred', alpha=0.7, edgecolor='black', zorder=3)
    
    ax_polar.set_thetamin(-25)
    ax_polar.set_thetamax(75)
    ax_polar.set_theta_zero_location('E')
    
    # 10度刻みの罫線
    ax_polar.set_xticks(np.deg2rad(bins))
    ax_polar.set_xticklabels([f"{a}°" for a in bins], fontsize=10, fontweight='bold')
    
    # 半径の目盛り（打率なので0.0〜1.0）
    ax_polar.set_ylim(0, max(avg_list) + 0.1 if max(avg_list) > 0 else 1.0)
    ax_polar.set_yticklabels([f".{int(y*1000):03d}" for y in ax_polar.get_yticks()], fontsize=8)

    # 各棒の上に数値を表示（打率とサンプル数）
    for t, a, n in zip(theta, avg_list, n_list):
        if n > 0:
            ax_polar.text(t, a + 0.02, f".{int(a*1000):03d}\n(n={n})", 
                        ha='center', va='bottom', fontsize=8, fontweight='bold', zorder=10)

    # バレルゾーン(25-35度)の強調
    ax_polar.fill_between(np.deg2rad([25, 35]), 0, 1.0, color='orange', alpha=0.1, zorder=2)
    
    st.pyplot(fig_polar)
    st.caption("※半径の長さは打率を表します。nは各角度での打球数です。")
else:
    st.info("打撃結果データ(PlayResult)が不足しているため、打率を計算できません。")
