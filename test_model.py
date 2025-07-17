# Libraries
import torch
import wandb
import time
import lightning as L
from torch_geometric.data import DataLoader
from lightning.pytorch.loggers import WandbLogger

from utils.dataset import create_model_dataset, to_temporal_dataset
from utils.dataset import get_temporal_test_dataset_parameters
from utils.load import read_config
from utils.miscellaneous import (
    get_numerical_times,
    get_speed_up,
    get_model,
    SpatialAnalysis,
    fix_dict_in_config,
)
from training.train import LightningTrainer

torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = True
torch.set_float32_matmul_precision("high")


def main(config):
    L.seed_everything(config.models["seed"])

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    dataset_parameters = config.dataset_parameters
    scalers = config.scalers
    selected_node_features = config.selected_node_features
    selected_edge_features = config.selected_edge_features

    # Create test dataset
    _, _, test_dataset, scalers = create_model_dataset(
        scalers=scalers,
        device=device,
        **dataset_parameters,
        **selected_node_features,
        **selected_edge_features,
    )

    temporal_test_dataset_parameters = get_temporal_test_dataset_parameters(
        config, config.temporal_dataset_parameters
    )
    temporal_test_dataset = to_temporal_dataset(
        test_dataset, rollout_steps=-1, **temporal_test_dataset_parameters
    )
    test_dataloader = DataLoader(temporal_test_dataset, batch_size=20, shuffle=False)

    num_node_features = temporal_test_dataset[0].x.size(-1)
    num_edge_features = temporal_test_dataset[0].edge_attr.size(-1)
    previous_t = temporal_test_dataset_parameters["previous_t"]
    test_size = len(test_dataset)
    test_dataset_name = dataset_parameters["test_dataset_name"]
    temporal_res = dataset_parameters["temporal_res"]
    model_parameters = config.models
    model_type = model_parameters.pop("model_type")

    if model_type == "MSGNN":
        num_scales = test_dataset[0].mesh.num_meshes
        model_parameters["num_scales"] = num_scales

    # Create model
    model = get_model(model_type)(
        num_node_features=num_node_features,
        num_edge_features=num_edge_features,
        previous_t=previous_t,
        device=device,
        **model_parameters,
    ).to(device)

    trainer_options = config.trainer_options
    lr_info = config["lr_info"]

    # info for testing dataset
    plmodule = LightningTrainer(
        model, lr_info, trainer_options, temporal_test_dataset_parameters
    )

    # Load trained model
    plmodule_kwargs = {
        "model": model,
        "lr_info": lr_info,
        "trainer_options": trainer_options,
        "temporal_test_dataset_parameters": temporal_test_dataset_parameters,
    }

    model = plmodule.load_from_checkpoint(
        config.saved_model, map_location=device, **plmodule_kwargs
    )
    model = plmodule.model.to(device)

    # Numerical simulation times
    maximum_time = test_dataset[0].WD.shape[1]
    numerical_times = get_numerical_times(
        test_dataset_name + "_test",
        test_size,
        temporal_res,
        maximum_time,
        **temporal_test_dataset_parameters,
        overview_file="database/overview.csv",
    )

    # Define trainer
    trainer = L.Trainer(accelerator="auto", devices="auto")

    start_time = time.time()
    predicted_rollout = trainer.predict(plmodule, dataloaders=test_dataloader)
    prediction_times = time.time() - start_time
    prediction_times = prediction_times / len(temporal_test_dataset)
    predicted_rollout = [item for roll in predicted_rollout for item in roll]

    spatial_analyser = SpatialAnalysis(
        predicted_rollout,
        prediction_times,
        test_dataset,
        **temporal_test_dataset_parameters,
    )

    rollout_loss = spatial_analyser._get_rollout_loss(type_loss="MAE")
    model_times = spatial_analyser.prediction_times

    print("test roll loss WD:", rollout_loss.mean(0)[0].item())
    print("test roll loss V:", rollout_loss.mean(0)[1:].mean().item())

    # Speed up
    avg_speedup, std_speedup = get_speed_up(numerical_times, model_times)

    print(
        f"test CSI_005: {spatial_analyser._get_CSI(water_threshold=0.05).nanmean().item()}"
    )
    print(
        f"test CSI_03: {spatial_analyser._get_CSI(water_threshold=0.3).nanmean().item()}"
    )
    print(f"mean speed-up: {avg_speedup:.2f}\nstd speed-up: {std_speedup:.3f}")

    print("Testing finished!")


if __name__ == "__main__":
    # Read configuration file with parameters
    cfg = read_config("config_finetune.yaml")

    wandb_logger = WandbLogger(mode="disabled", config=cfg)

    fix_dict_in_config(wandb)

    config = wandb.config

    main(config)
