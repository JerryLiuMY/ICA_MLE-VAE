from global_settings import VAE_PATH
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from torch import nn
import numpy as np
import pandas as pd
import seaborn as sns
import os
sns.set()
palette = sns.color_palette()


def plot_recon_2d(m, n):
    """ Visualize the reconstructed 2D latent space
    :param m: dimension of the latent variable
    :param n: dimension of the target variable
    :return: dataframe of z and x
    """

    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    activations = [nn.ReLU(), nn.Sigmoid(), nn.Tanh(), nn.GELU()]
    for ax, activation in zip(axes, activations):
        # load simu_df and recon_df and perform PCA
        activation_name = ''.join([_ for _ in str(activation) if _.isalpha()])
        simu_pca, recon_pac = PCA(n_components=2), PCA(n_components=2)
        model_path = os.path.join(VAE_PATH, f"m{m}_n{n}_{activation_name}")
        simu_df = pd.read_csv(os.path.join(model_path, "simu_df.csv"), index_col=0)
        recon_df = pd.read_csv(os.path.join(model_path, "recon_df.csv"), index_col=0)
        simu_2d = simu_pca.fit_transform(simu_df.loc[:, [_ for _ in simu_df.columns if "x" in _]])
        recon_2d = recon_pac.fit_transform(recon_df.loc[:, [_ for _ in recon_df.columns if "mean" in _]])
        simu_2d_df = pd.DataFrame(simu_2d, columns=["pc0", "pc1"])
        recon_2d_df = pd.DataFrame(recon_2d, columns=["pc0", "pc1"])

        # visualization of the 2d PCA distribution
        sns.kdeplot(data=simu_2d_df, x="pc0", y="pc1", fill=True, alpha=1., ax=ax)
        sns.kdeplot(data=recon_2d_df, x="pc0", y="pc1", fill=True, alpha=.7, ax=ax)
        s2 = np.round(np.mean(np.exp(recon_df["logs2"])), 3)
        ax_legend_true = mpatches.Patch(color=palette[0], label="Observed $p(x|z)$", alpha=0.8)
        ax_legend_recon = mpatches.Patch(color=palette[1], label="Recon $\widehat{p}(x|z)$", alpha=0.8)
        ax_legend_s2 = mpatches.Patch(color=palette[7], label="$\widehat{\sigma}^2$" + f"={s2}", alpha=0.8)
        handles = [ax_legend_true, ax_legend_recon, ax_legend_s2]
        ax.legend(handles=handles, loc="upper right", handlelength=0.2, handletextpad=0.5)
        ax.set_title(f"Reconstruction of {activation_name}")
        ax.set_xlabel("PC0")
        ax.set_ylabel("PC1")

    plt.tight_layout()

    return fig