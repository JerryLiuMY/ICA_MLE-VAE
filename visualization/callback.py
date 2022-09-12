import matplotlib.pyplot as plt
from global_settings import PATH_DICT
from torch import nn
import numpy as np
import seaborn as sns
import os
sns.set()


def plot_callback(m, n, model_name, llh_method):
    """ Plot training and validation history
    :param m: dimension of the latent variable
    :param n: dimension of the target variable
    :param model_name: model name
    :param llh_method: method for numerical integration
    :return: dataframe of z and x
    """

    fig, axes = plt.subplots(2, 2, figsize=(14, 7))
    activations = [nn.ReLU(), nn.Sigmoid(), nn.Tanh(), nn.LeakyReLU()]
    axes = [ax for sub_axes in axes for ax in sub_axes]

    for ax, activation in zip(axes, activations):
        activation_name = ''.join([_ for _ in str(activation) if _.isalpha()])
        model_path = os.path.join(PATH_DICT[model_name], f"m{m}_n{n}_{activation_name}")
        train_llh = np.load(os.path.join(model_path, f"train_llh_{llh_method}.npy"))
        valid_llh = np.load(os.path.join(model_path, f"valid_llh_{llh_method}.npy"))

        ax.set_title(f"Learning curve of {activation_name} [Integration = {llh_method}]")
        ax.plot(train_llh, color=sns.color_palette()[0], label="train_llh")
        ax.plot(valid_llh, color=sns.color_palette()[1], label="valid_llh")
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Log-Likelihood")

        if model_name == "vae":
            ax_ = ax.twinx()
            train_loss = np.load(os.path.join(model_path, "train_loss.npy"))
            valid_loss = np.load(os.path.join(model_path, "valid_loss.npy"))
            ax_.plot(train_loss, color=sns.color_palette()[2], label="train_loss")
            ax_.plot(valid_loss, color=sns.color_palette()[3], label="valid_loss")
            ax_.set_ylabel("ELBO")
            ax_.grid(False)

            handles, labels = ax.get_legend_handles_labels()
            handles_, labels_ = ax_.get_legend_handles_labels()
            ax.legend(handles + handles_, labels + labels_, loc="upper right")

        elif "mle" in model_name:
            handles, labels = ax.get_legend_handles_labels()
            ax.legend(handles, labels, loc="upper right")

        else:
            raise ValueError("Invalid model name")

    plt.tight_layout()

    return fig
