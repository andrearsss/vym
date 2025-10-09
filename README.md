## vym

Flutter app leveraging AI for fitness

## Project Structure
The project is structured in two main folders:

- **/app**: This folder contains the Flutter client app (Android-only at the moment). The app works together with my forked YOLO plugin ([app/plugins/yolo-flutter-plugin](https://github.com/andrearsss/yolo-flutter-plugin/)), which was adapted for custom pose model inference and native Android keypoints processing for exercise form analysis
- **/services**: This folder hosts the microservices backend that powers the app.
- - /api-gateway: FastAPI main access point
- - /auth: FastAPI service for authentication and authorization
- - /auth-db: Postgres DB for account storage
- - /image-storage: FastAPI service image storage into local MinIO S3 bucket
- - TBD: services for training, model registry and data ingestion
