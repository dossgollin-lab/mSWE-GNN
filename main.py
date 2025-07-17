# Libraries
import torch
import wandb
import time
import matplotlib.pyplot as plt
import lightning as L
from torch_geometric.data import DataLoader
from lightning.pytorch.loggers import WandbLogger
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint

from utils.dataset import create_model_dataset, to_temporal_dataset
from utils.dataset import get_temporal_test_dataset_parameters
from utils.load import read_config
from utils.visualization import PlotRollout
from utils.miscellaneous import (
    get_numerical_times,
    get_speed_up,
    get_model,
    SpatialAnalysis,
    fix_dict_in_config,
)
from training.train import LightningTrainer, DataModule, CurriculumLearning

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

    train_dataset, val_dataset, test_dataset, scalers = create_model_dataset(
        scalers=scalers,
        device=device,
        **dataset_parameters,
        **selected_node_features,
        **selected_edge_features,
    )

    temporal_dataset_parameters = config.temporal_dataset_parameters
    temporal_train_dataset = to_temporal_dataset(
        train_dataset, **temporal_dataset_parameters
    )

    print("Number of training simulations:\t", len(train_dataset))
    print("Number of training samples:\t", len(temporal_train_dataset))
    print("Number of node features:\t", temporal_train_dataset[0].x.shape[-1])
    print("Number of rollout steps:\t", temporal_train_dataset[0].y.shape[-1])

    num_node_features, num_edge_features = temporal_train_dataset[0].x.size(
        -1
    ), temporal_train_dataset[0].edge_attr.size(-1)
    num_nodes, num_edges = temporal_train_dataset[0].x.size(0), temporal_train_dataset[
        0
    ].edge_attr.size(0)

    previous_t = temporal_dataset_parameters["previous_t"]
    test_size = len(test_dataset)
    test_dataset_name = dataset_parameters["test_dataset_name"]
    temporal_res = dataset_parameters["temporal_res"]
    max_rollout_steps = temporal_dataset_parameters["rollout_steps"]

    print("Temporal resolution:\t", temporal_res, "min")

    model_parameters = config.models
    model_type = model_parameters.pop("model_type")

    if model_type == "MSGNN":
        num_scales = train_dataset[0].mesh.num_meshes
        model_parameters["num_scales"] = num_scales

    model = get_model(model_type)(
        num_node_features=num_node_features,
        num_edge_features=num_edge_features,
        previous_t=previous_t,
        device=device,
        **model_parameters,
    ).to(device)

    trainer_options = config.trainer_options
    type_loss = trainer_options["type_loss"]
    lr_info = config["lr_info"]

    # info for testing dataset
    temporal_test_dataset_parameters = get_temporal_test_dataset_parameters(
        config, temporal_dataset_parameters
    )

    temporal_val_dataset = to_temporal_dataset(
        val_dataset, rollout_steps=-1, **temporal_test_dataset_parameters
    )

    plmodule = LightningTrainer(
        model, lr_info, trainer_options, temporal_test_dataset_parameters
    )

    pldatamodule = DataModule(
        temporal_train_dataset,
        temporal_val_dataset,
        batch_size=trainer_options["batch_size"],
    )

    # Number of parameters
    total_parameteres = sum(p.numel() for p in model.parameters())
    wandb.log({"total parameters": total_parameteres})

    # Training
    # Define callbacks
    checkpoint_callback = ModelCheckpoint(
        dirpath="lightning_logs/models", monitor="val_loss", mode="min", save_top_k=1
    )
    curriculum_callback = CurriculumLearning(max_rollout_steps, patience=5)
    early_stopping = EarlyStopping(
        "val_CSI_005", mode="max", patience=trainer_options["patience"]
    )
    wandb_logger.watch(model, log="all", log_graph=False)

    # Load trained model
    plmodule_kwargs = {
        "model": model,
        "lr_info": lr_info,
        "trainer_options": trainer_options,
        "temporal_test_dataset_parameters": temporal_test_dataset_parameters,
    }

    if "saved_model" in config:
        model = plmodule.load_from_checkpoint(
            config["saved_model"], map_location=device, **plmodule_kwargs
        )

    # Define trainer
    trainer = L.Trainer(
        accelerator="auto",
        devices="auto",
        max_epochs=trainer_options["max_epochs"],
        gradient_clip_val=1,
        precision="16-mixed",
        enable_progress_bar=False,
        logger=wandb_logger,
        callbacks=[
            checkpoint_callback,
            curriculum_callback,
            early_stopping,
        ],
    )

    # Train and get trained model
    trainer.fit(plmodule, pldatamodule)

    # Load the best model checkpoint
    plmodule = plmodule.load_from_checkpoint(
        checkpoint_callback.best_model_path, map_location=device, **plmodule_kwargs
    )
    model = plmodule.model.to(device)

    # validate with trained model
    trainer.validate(plmodule, pldatamodule)

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

    # Rollout error and time
    temporal_test_dataset = to_temporal_dataset(
        test_dataset, rollout_steps=-1, **temporal_test_dataset_parameters
    )

    test_dataloader = DataLoader(
        temporal_test_dataset, batch_size=len(temporal_test_dataset), shuffle=False
    )

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

    rollout_loss = spatial_analyser._get_rollout_loss(type_loss=type_loss)
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

    wandb.log(
        {
            "speed-up": avg_speedup,
            "test roll loss WD": rollout_loss.mean(0)[0].item(),
            "test roll loss V": rollout_loss.mean(0)[1:].mean().item(),
            "test CSI_005": spatial_analyser._get_CSI(water_threshold=0.05)
            .nanmean()
            .item(),
            "test CSI_03": spatial_analyser._get_CSI(water_threshold=0.3)
            .nanmean()
            .item(),
        }
    )

    fig, _ = spatial_analyser.plot_CSI_rollouts(water_thresholds=[0.05, 0.3])
    plt.savefig("results/CSI.png")

    best_id = rollout_loss.mean(1).argmin().item()
    worst_id = rollout_loss.mean(1).argmax().item()

    for id_dataset, name in zip([best_id, worst_id], ["best", "worst"]):
        rollout_plotter = PlotRollout(
            model.to(device),
            test_dataset[id_dataset].to(device),
            scalers=scalers,
            type_loss=type_loss,
            **temporal_test_dataset_parameters,
        )
        if model_type == "MSGNN":
            fig = rollout_plotter.explore_rollout(scale=0)
        else:
            fig = rollout_plotter.explore_rollout()
        plt.savefig(f"results/simulation_{name}.png")

    print("Training and testing finished!")


if __name__ == "__main__":
    # Read configuration file with parameters
    cfg = read_config("config.yaml")

    wandb_logger = WandbLogger(
        log_model=True,
        # mode='disabled',
        config=cfg,
    )

    fix_dict_in_config(wandb)

    config = wandb.config

    main(config)
