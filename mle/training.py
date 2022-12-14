from tools.params import mle_dict as train_dict
from global_settings import DEVICE
from tools.params import sigma
from datetime import datetime
from mle.model import MLE
import numpy as np
import torch


def train_mle(m, n, activation, train_loader, valid_loader, train_s2, decoder_dgp, llh_func, grad_method):
    """ Perform autograd to train the model and find logs2
    :param m: latent dimension
    :param n: observed dimension
    :param activation: activation function for mlp
    :param train_loader: training dataset loader
    :param valid_loader: validation dataset loader
    :param train_s2: whether to train s2 or not
    :param decoder_dgp: whether to use the same decoder as dgp
    :param llh_func: function for numerical integration
    :param grad_method: method for computing the gradient
    :return: trained model and training loss history
    """

    # load parameters
    epochs, lr = train_dict["epochs"], train_dict["lr"]

    # building Autograd
    model = MLE(m, n, activation, fit_s2=False, decoder_dgp=decoder_dgp)
    model = model.to(DEVICE)
    if train_s2:
        logs2 = torch.tensor([0.], requires_grad=True).to(DEVICE)
    else:
        logs2 = torch.tensor([np.log(sigma**2)], requires_grad=False).to(DEVICE)

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
            x_batch = x_batch.to(DEVICE)
            logs2_batch = logs2.repeat(x_batch.shape[0], 1)
            if grad_method == "auto":
                objective = - llh_func(m, n, x_batch, model, logs2_batch).sum(dim=0)
                optimizer.zero_grad()
                objective.backward()
                optimizer.step()
                llh_batch = objective.neg().cpu().detach().numpy().tolist()
            elif grad_method == "sgd":
                objective = - llh_func(m, n, x_batch, model, logs2_batch).exp()
                likelihood = - torch.clone(objective)
                gradient = likelihood.pow(-1).detach()
                optimizer.zero_grad()
                objective.backward(gradient=gradient)
                optimizer.step()
                llh_batch = objective.neg().log().sum(dim=0).cpu().detach().numpy().tolist()
            else:
                raise ValueError("Invalid backpropagation method")

            train_llh += llh_batch / x_batch.size(dim=0)
            nbatch += 1

        # get training llh
        scheduler.step()
        train_llh = train_llh / nbatch
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Finish training with llh={round(train_llh, 2)}")
        train_llh_li.append(train_llh)

        # get validation loss
        valid_llh = valid_mle([model, logs2], valid_loader, llh_func, eval_mode=False)
        valid_llh_li.append(valid_llh)

    # return train/valid history and log-likelihoods
    train_llh_arr = np.array(train_llh_li)
    valid_llh_arr = np.array(valid_llh_li)
    callback = {"llh": [train_llh_arr, valid_llh_arr]}

    return [model, logs2], callback


def valid_mle(inputs, valid_loader, llh_func, eval_mode):
    """ Training VAE with the specified image dataset
    :param inputs: trained VAE model and log of the fitted s2
    :param valid_loader: validation dataset loader
    :param llh_func: function for numerical integration
    :param eval_mode: whether set to evaluation model
    :return: validation loss
    """

    # load parameters and set evaluation mode
    [model, logs2] = inputs
    m, n = model.m, model.n
    if eval_mode:
        model.eval()

    # get validation loss
    valid_llh, nbatch = 0., 0
    for x_batch, _ in valid_loader:
        with torch.no_grad():
            x_batch = x_batch.to(DEVICE)
            logs2_batch = logs2.repeat(x_batch.shape[0], 1)

            llh_sample = llh_func(m, n, x_batch, model, logs2_batch)
            llh_batch = llh_sample.sum(dim=0).cpu().detach().numpy().tolist()
            valid_llh += llh_batch / x_batch.size(dim=0)
            nbatch += 1

    valid_llh = valid_llh / nbatch
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Finish validation with llh={round(valid_llh, 2)}")

    return valid_llh
