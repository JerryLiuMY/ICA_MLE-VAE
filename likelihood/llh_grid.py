import itertools
import numpy as np
import torch
from global_settings import device
from likelihood.dist import get_normal_lp
from params.params import min_lim, max_lim, space


def get_llh_grid(m, n, x, model, logs2):
    """ Find log-likelihood from data and trained model
    :param m: latent dimension
    :param n: observed dimension
    :param x: inputs related to the observation x data
    :param model: trained model
    :param logs2: log of the estimated s2
    :return: log-likelihood
    """

    # define input
    data_size = x.size(dim=0)

    # prepare for numerical integration
    lin_space = np.linspace(min_lim, max_lim, space)
    grid_space = np.array([0.5 * (lin_space[i] + lin_space[i + 1]) for i in range(len(lin_space) - 1)])
    volume = ((max_lim - min_lim) / (space - 1)) ** m
    volume = torch.tensor(volume)

    # get reconstruction -- data_size x grid_size x n
    z_grid = itertools.product(*[list(grid_space) for _ in range(m)])
    z_grid = np.array(list(z_grid)).astype(np.float32)
    z_grid = torch.tensor(z_grid)
    grid_size = z_grid.shape[0]
    z_grid = z_grid.repeat(data_size, 1, 1).reshape(data_size, grid_size, m)
    z_grid = z_grid.to(device)
    x_recon = model.decoder(z_grid)[0]

    # get covariance -- data_size x grid_size x n x n
    s2_sqrt = logs2.exp().sqrt()
    s2_sqrt = s2_sqrt.repeat(1, n * n).reshape(data_size, n, n)
    s2_sqrt = s2_sqrt.repeat(1, grid_size, 1, 1).reshape(data_size, grid_size, n, n)
    eye = torch.eye(n).repeat(grid_size, 1, 1).reshape(grid_size, n, n)
    eye = eye.repeat(data_size, 1, 1, 1).reshape(data_size, grid_size, n, n)
    eye = eye.to(device)
    s2_cov_tril = s2_sqrt * eye

    # get input x -- data_size x grid_size x n
    x = x.repeat(1, grid_size).reshape(data_size, grid_size, n)

    # perform numerical integration
    log_prob_1 = get_normal_lp(x, loc=x_recon, cov_tril=s2_cov_tril)
    log_prob_2 = get_normal_lp(z_grid, loc=torch.zeros(z_grid.shape[-1]), cov_tril=torch.eye(z_grid.shape[-1]))
    log_prob_3 = torch.log(volume)
    llh = log_prob_1 + log_prob_2 + log_prob_3
    llh = llh.to(torch.float64)
    llh_sample = llh.exp().sum(dim=1).log()
    llh_sample = torch.nan_to_num(llh_sample, neginf=np.log(torch.finfo(torch.float64).tiny))
    llh_batch = llh_sample.sum(dim=0)

    return llh_batch