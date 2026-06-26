import pytest
import torch

from backend.nn_trainer import TrainingConfig, VolatilityDataset, VolatilityModel


def test_volatility_model_forward_shape():
    config = TrainingConfig(window_size=5, rnn_hidden_size=4, fc_hidden_size=3)
    model = VolatilityModel(config)
    x = torch.ones((2, config.window_size, 1), dtype=torch.float32)

    y = model(x)

    assert tuple(y.shape) == (2,)


def test_volatility_dataset_length_and_item():
    X = [[[0.1]], [[0.2]]]
    y = [0.11, 0.21]
    dataset = VolatilityDataset(X, y)

    item_X, item_y = dataset[0]

    assert len(dataset) == 2
    assert tuple(item_X.shape) == (1, 1)
    assert float(item_y) == pytest.approx(y[0])
