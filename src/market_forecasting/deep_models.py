from __future__ import annotations

import copy
import math

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 512) -> None:
        super().__init__()
        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
        pe = torch.zeros(max_len, d_model)
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:, : x.size(1)]


class SequenceTransformerRegressor(nn.Module):
    def __init__(
        self,
        input_dim: int,
        *,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 2,
        dim_feedforward: int = 128,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.input_projection = nn.Linear(input_dim, d_model)
        self.position_encoding = PositionalEncoding(d_model=d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.head = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 2, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        encoded = self.input_projection(x)
        encoded = self.position_encoding(encoded)
        encoded = self.encoder(encoded)
        return self.head(encoded[:, -1, :]).squeeze(-1)


def cuda_available() -> bool:
    return torch.cuda.is_available()


def train_sequence_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    *,
    epochs: int,
    learning_rate: float,
    device: str,
    random_state: int,
) -> SequenceTransformerRegressor:
    torch.manual_seed(random_state)
    model = SequenceTransformerRegressor(input_dim=X_train.shape[-1]).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    loss_fn = nn.MSELoss()

    val_size = int(len(X_train) * 0.15)
    if val_size >= 8:
        train_slice = slice(0, len(X_train) - val_size)
        val_slice = slice(len(X_train) - val_size, len(X_train))
        X_fit, y_fit = X_train[train_slice], y_train[train_slice]
        X_val, y_val = X_train[val_slice], y_train[val_slice]
    else:
        X_fit, y_fit = X_train, y_train
        X_val = y_val = None

    dataset = TensorDataset(
        torch.tensor(X_fit, dtype=torch.float32),
        torch.tensor(y_fit, dtype=torch.float32),
    )
    loader = DataLoader(dataset, batch_size=min(64, max(8, len(dataset))), shuffle=True)

    best_state = copy.deepcopy(model.state_dict())
    best_loss = float("inf")
    patience = 0

    for _ in range(epochs):
        model.train()
        for xb, yb in loader:
            xb = xb.to(device)
            yb = yb.to(device)
            optimizer.zero_grad()
            predictions = model(xb)
            loss = loss_fn(predictions, yb)
            loss.backward()
            optimizer.step()

        if X_val is None:
            best_state = copy.deepcopy(model.state_dict())
            continue

        model.eval()
        with torch.no_grad():
            val_pred = model(torch.tensor(X_val, dtype=torch.float32, device=device))
            val_loss = float(loss_fn(val_pred, torch.tensor(y_val, dtype=torch.float32, device=device)).item())

        if val_loss < best_loss:
            best_loss = val_loss
            best_state = copy.deepcopy(model.state_dict())
            patience = 0
        else:
            patience += 1
            if patience >= 10:
                break

    model.load_state_dict(best_state)
    model.eval()
    return model


def predict_sequence_model(model: SequenceTransformerRegressor, X: np.ndarray, *, device: str) -> np.ndarray:
    if len(X) == 0:
        return np.asarray([], dtype=np.float32)
    with torch.no_grad():
        tensor = torch.tensor(X, dtype=torch.float32, device=device)
        return model(tensor).detach().cpu().numpy()
