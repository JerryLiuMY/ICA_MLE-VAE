from params.params import mle_dict as train_dict
from global_settings import device
from datetime import datetime
from mle.model import MLE
import numpy as np
import torch


def train_mleauto(m, n, train_loader, valid_loader, llh_func):
    """ Perform autograd to train the model and find logs2
    :param m: latent dimension
    :param n: observed dimension
    :param train_loader: training dataset loader
    :param valid_loader: validation dataset loader
    :param llh_func: function for numerical integration
    :return: trained model and training loss history
    """

    # load parameters
    epochs, lr = train_dict["epochs"], train_dict["lr"]

    # building Autograd
    model = MLE(m, n)
    logs2 = torch.tensor([0.], requires_grad=True).to(device)
    optimizer = torch.optim.AdamW([*model.parameters(), logs2], lr=lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, 1, gamma=0.995)
    num_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Number of model parameters: {num_params}")

    # training loop
    model.train()
    train_llh_li, valid_llh_li = [], []

    for epoch in range(epochs):
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Training on epoch {epoch} "
              f"[lr={round(scheduler.get_last_lr()[0], 6)}]...")

        # mini-batch loop
        train_llh, nbatch = 0., 0
        for x_batch, _ in train_loader:
            x_batch = x_batch.to(device)
            logs2_batch = logs2.repeat(x_batch.shape[0], 1)
            llh = - llh_func(m, n, x_batch, model, logs2_batch)
            optimizer.zero_grad()
            llh.backward()
            optimizer.step()

            llh_batch = - llh.cpu().detach().numpy().tolist()
            train_llh += llh_batch / x_batch.size(dim=0)
            nbatch += 1

        # get training llh
        scheduler.step()
        train_llh = train_llh / nbatch
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Finish training with llh={round(train_llh, 2)}")
        train_llh_li.append(train_llh)

        # get validation loss
        valid_llh = valid_mleauto(m, n, model, valid_loader, llh_func, eval_mode=False)
        valid_llh_li.append(valid_llh)

    # return train/valid history and log-likelihoods
    train_llh_arr = np.array(train_llh_li)
    valid_llh_arr = np.array(valid_llh_li)
    callback = {"llh": [train_llh_arr, valid_llh_arr]}

    return model, callback


def valid_mleauto(m, n, model, valid_loader, llh_func, eval_mode):
    """ Training VAE with the specified image dataset
    :param m: dimension of the latent variable
    :param n: dimension of the target variable
    :param model: trained VAE model
    :param valid_loader: validation dataset loader
    :param llh_func: function for numerical integration
    :param eval_mode: whether set to evaluation model
    :return: validation loss
    """

    # set evaluation mode
    if eval_mode:
        model.eval()

    # get validation loss
    valid_llh, nbatch = 0., 0
    for x_batch, _ in valid_loader:
        with torch.no_grad():
            x_batch = x_batch.to(device)
            logs2_batch = torch.zeros(size=(x_batch.shape[0], 1)).to(device)

            llh_batch = llh_func(m, n, x_batch, model, logs2_batch).cpu().detach().numpy().tolist()
            valid_llh += llh_batch / x_batch.size(dim=0)
            nbatch += 1

    valid_llh = valid_llh / nbatch
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Finish validation with llh={round(valid_llh, 2)}")

    return valid_llh
