from torch.nn import functional as F
from models.vae import VariationalAutoencoder
from params.params import train_dict
from global_settings import device
from datetime import datetime
import torch
import numpy as np


def train_vae(train_loader):
    """ Training VAE with the specified image dataset
    :param train_loader: training image dataset loader
    :return: trained model and training loss history
    """

    # load parameters
    epoch, lr, beta = train_dict["epoch"], train_dict["lr"], train_dict["beta"]

    # building VAE
    model = VariationalAutoencoder()
    model = model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, 1, gamma=0.8)
    num_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Number of parameters: {num_params}")

    # training loop
    model.train()
    train_loss = []
    for epoch in range(epoch):
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Training on epoch {epoch}...")
        epoch_loss, nbatch = 0., 0

        for train_batch, _ in train_loader:
            train_batch = train_batch.to(device)
            train_batch_recon, mu, logvar = model(train_batch)
            loss = vae_loss(train_batch_recon, train_batch, mu, logvar, beta)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            # update loss and nbatch
            epoch_loss += loss.item()
            nbatch += 1

        scheduler.step()

        # append training loss
        epoch_loss = epoch_loss / nbatch
        train_loss.append(epoch_loss)
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Finish epoch {epoch} with loss {epoch_loss}")

    train_loss = np.array(train_loss)

    return model, train_loss


def vae_loss(x_recon, x, mu, logvar, beta):
    """ Calculating loss for variational autoencoder
    :param x_recon: reconstructed image
    :param x: original image
    :param mu: mean in the hidden layer
    :param logvar: log of the variance in the hidden layer
    :param beta: beta
    :return: reconstruction loss + KL
    """

    # reconstruction loss (dependent of image resolution)
    recon_loss = F.binary_cross_entropy(x_recon.view(-1, 784), x.view(-1, 784), reduction="sum")

    # KL-divergence
    kl_div = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())

    return recon_loss + beta * kl_div