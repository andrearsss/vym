import os
import mlflow
import mlflow.pytorch
from ultralytics import YOLO, settings
from pathlib import Path
import yaml
import numpy as np


class YOLOTrainer:
    
    def __init__(self, mlflow_tracking_uri: str = None):
        self.mlflow_tracking_uri = mlflow_tracking_uri or os.getenv(
            "MLFLOW_TRACKING_URI", "http://mlflow:5000"
        )
        mlflow.set_tracking_uri(self.mlflow_tracking_uri)
        
    def setup_experiment(self, experiment_name: str = "yolo-training"):
        mlflow.set_experiment(experiment_name)
        
    def train(
        self,
        model_name: str = "yolo11n.pt",
        data_yaml: str = "dataset_example.yaml",
        epochs: int = 10,
        imgsz: int = 640,
        batch: int = 16,
        lr0: float = 0.01,
        momentum: float = 0.937,
        weight_decay: float = 0.0005,
        device: str = "0",
        project_name: str = "runs/train",
        run_name: str = None,
        **kwargs
    ):
        """
        Loads a YOLO model, starts training, and logs parameters, metrics, and artifacts to MLflow.
        """
        
        with mlflow.start_run(run_name=run_name) as run:
            print(f"MLflow Run ID: {run.info.run_id}")
            print(f"MLflow Tracking URI: {self.mlflow_tracking_uri}")
            
            # Log parameters
            params = {
                "model_name": model_name,
                "data_yaml": data_yaml,
                "epochs": epochs,
                "imgsz": imgsz,
                "batch": batch,
                "lr0": lr0,
                "momentum": momentum,
                "weight_decay": weight_decay,
                "device": device,
                "optimizer": "AdamW",
            }
            params.update(kwargs)
            mlflow.log_params(params)
            
            # Log dataset info
            if os.path.exists(data_yaml):
                with open(data_yaml, 'r') as f:
                    dataset_config = yaml.safe_load(f)
                    mlflow.log_dict(dataset_config, "dataset_config.yaml")
                    if 'names' in dataset_config:
                        mlflow.log_param("num_classes", len(dataset_config['names']))
            else:
                print(f"Unable to find dataset yaml {data_yaml}. Aborting training.")
                return None, run.info.run_id
            
            # Load model
            print(f"Loading model: {model_name}")
            model = YOLO(model_name)
            mlflow.log_param("model_type", model.model_name)
            
            print("Starting training...")
            results = model.train(
                data=data_yaml,
                epochs=epochs,
                imgsz=imgsz,
                batch=batch,
                lr0=lr0,
                momentum=momentum,
                weight_decay=weight_decay,
                device=device,
                project=project_name,
                name=run.info.run_id,
                exist_ok=True,
                **kwargs
            )
            
            train_dir = Path(project_name) / run.info.run_id
            
            # Log metrics from results
            if hasattr(results, 'results_dict'):
                for key, value in results.results_dict.items():
                    if isinstance(value, (int, float)):
                        # escape invalid characters like '(' and ')' in the key name
                        sanitized_key = key.replace("(", "_").replace(")", "")
                        mlflow.log_metric(sanitized_key, value)
            
            # Log training curves and results
            self._log_training_artifacts(train_dir)
            
            # Log the best model
            best_model_path = train_dir / "weights" / "best.pt"
            last_model_path = train_dir / "weights" / "last.pt"
            
            if best_model_path.exists():
                mlflow.log_artifact(str(best_model_path), "models")
                print(f"Logged best model: {best_model_path}")
                
            if last_model_path.exists():
                mlflow.log_artifact(str(last_model_path), "models")
                print(f"Logged last model: {last_model_path}")
            
            # Log the final model using MLflow's pytorch format
            try:
                # Save model in MLflow format
                mlflow.pytorch.log_model(
                    model.model,
                    name=run_name,
                    input_example=np.zeros((3, 640, 640), dtype=np.float64),
                    registered_model_name=f"yolo_{model_name.replace('.pt', '')}"
                )
                print("Model logged in MLflow PyTorch format")
            except Exception as e:
                print(f"Could not log PyTorch model: {e}")
            
            # Log results summary
            results_file = train_dir / "results.csv"
            if results_file.exists():
                mlflow.log_artifact(str(results_file), "metrics")
            
            print(f"\nTraining completed!")
            print(f"Run ID: {run.info.run_id}")
            print(f"Artifact URI: {mlflow.get_artifact_uri()}")
            
            return results, run.info.run_id
    
    def _log_training_artifacts(self, train_dir: Path):
        """Log training artifacts to MLflow"""
        
        # Log confusion matrix
        confusion_matrix = train_dir / "confusion_matrix.png"
        if confusion_matrix.exists():
            mlflow.log_artifact(str(confusion_matrix), "plots")
        
        # Log normalized confusion matrix
        confusion_matrix_normalized = train_dir / "confusion_matrix_normalized.png"
        if confusion_matrix_normalized.exists():
            mlflow.log_artifact(str(confusion_matrix_normalized), "plots")
        
        # Log training curves
        results_png = train_dir / "results.png"
        if results_png.exists():
            mlflow.log_artifact(str(results_png), "plots")
        
        # Log F1, PR, and P curves
        for curve_name in ["F1_curve.png", "PR_curve.png", "P_curve.png", "R_curve.png"]:
            curve_path = train_dir / curve_name
            if curve_path.exists():
                mlflow.log_artifact(str(curve_path), "plots")
        
        # Log validation batch predictions
        val_batch_dir = train_dir / "val_batch"
        if val_batch_dir.exists():
            for img in val_batch_dir.glob("*.jpg"):
                mlflow.log_artifact(str(img), "validation_samples")
        
        # Log training arguments
        args_yaml = train_dir / "args.yaml"
        if args_yaml.exists():
            mlflow.log_artifact(str(args_yaml), "config")


def main():
    """Example training execution"""
    print("Initialization...")

    # Disable mlflow callbacks embedded into ultralytics
    settings.update({"mlflow": False})
    
    trainer = YOLOTrainer()
    trainer.setup_experiment(experiment_name="yolo-detection")
    
    # Training config
    config = {
        "model_name": "yolo11n.pt",
        "data_yaml": "dataset_example.yaml",
        "epochs": 3,
        "imgsz": 640,
        "batch": 16,
        "lr0": 0.01,
        "momentum": 0.937,
        "weight_decay": 0.0005,
        "device": "0",
        "project_name": "runs/train",
        "run_name": "yolo11n_experiment",
        "patience": 50,  # Early stopping 
        "save": True,
        "save_period": -1,  # disabled
        "cache": False,
        "workers": 8,
        "cos_lr": False,
        "close_mosaic": 10,
        "amp": True,
        "fraction": 1.0,
        "profile": False,
        "overlap_mask": True,
        "mask_ratio": 4,
        "dropout": 0.0,
        "val": True,
    }
    
    # Start training
    print("=" * 60)
    print("Starting YOLO Training with MLflow Integration")
    print("=" * 60)
    try:
        results, run_id = trainer.train(**config)
        
        if results:
            print("\n" + "=" * 60)
            print(f"Training completed successfully!")
            print(f"MLflow Run ID: {run_id}")
            print(f"Check MLflow UI at: {trainer.mlflow_tracking_uri}")
            print("=" * 60)
    except Exception as e:
        print(f"\nAn error occurred during execution: {e}")
        print("Please ensure your dataset YAML and model file are correctly set up.")


if __name__ == "__main__":
    main()
