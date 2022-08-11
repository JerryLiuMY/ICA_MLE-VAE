import torch.nn.functional as F
import torch.nn as nn
import torch


class VariationalAutoencoder(nn.Module):
    def __init__(self, m, n):
        super(VariationalAutoencoder, self).__init__()
        self.encoder = Encoder(m, n)
        self.decoder = Decoder(m, n)
        if not self.encoder.input_size == self.decoder.output_size:
            raise ValueError("Input size does not match with output size")

    def forward(self, x):
        mu, logvar = self.encoder(x)
        latent = self.latent_sample(mu, logvar)
        mean, logs2 = self.decoder(latent)

        return mean, logs2, mu, logvar

    def latent_sample(self, mu, logvar):
        # the re-parameterization trick
        if self.training:
            std = logvar.mul(0.5).exp_()
            eps = torch.empty_like(std).normal_()
            return eps.mul(std).add_(mu)
        else:
            return mu


class Block(nn.Module):
    def __init__(self, m, n):
        super(Block, self).__init__()
        self.input_size = n
        self.hidden = m


class Encoder(Block):
    def __init__(self, m, n):
        super(Encoder, self).__init__(m, n)

        # first encoder layer
        self.inter_size = self.input_size
        self.enc1 = nn.Linear(in_features=self.inter_size, out_features=self.inter_size)

        # second encoder layer
        self.enc2 = nn.Linear(in_features=self.inter_size, out_features=self.inter_size)

        # map to mu and variance
        self.fc_mu = nn.Linear(in_features=self.inter_size, out_features=self.hidden)
        self.fc_logvar = nn.Linear(in_features=self.inter_size, out_features=self.hidden)

    def forward(self, x):
        # encoder layers
        x = F.relu(self.enc1(x))
        x = F.relu(self.enc2(x))

        # calculate mu & logvar
        mu = self.fc_mu(x)
        logvar = self.fc_logvar(x)

        return mu, logvar


class Decoder(Encoder, Block):
    def __init__(self, m, n):
        super(Decoder, self).__init__(m, n)

        # linear layer
        self.fc = nn.Linear(in_features=self.hidden, out_features=self.inter_size)

        # first decoder layer
        self.dec2 = nn.Linear(in_features=self.inter_size, out_features=self.inter_size)

        # second decoder layer -- mean and logs2
        self.output_size = self.inter_size
        self.dec1_mean = nn.Linear(in_features=self.inter_size, out_features=self.output_size)
        self.dec1_logs2 = nn.Linear(in_features=self.inter_size, out_features=1)

    def forward(self, x):
        # linear layer
        x = self.fc(x)

        # decoder layers
        x = F.relu(self.dec2(x))
        mean = self.dec1_mean(x)
        logs2 = self.dec1_logs2(x)

        return mean, logs2