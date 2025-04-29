from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import *
from config import configuration


def main():
    spark = SparkSession.builder.appName("SmartCityStream") \
        .config("spark.jars.packages",
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,"
                "org.apache.hadoop:hadoop-aws:3.3.2,"
                "com.amazonaws:aws-java-sdk:1.12.262"
                ) \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.access.key", configuration.get('AWS_ACCESS_KEY')) \
        .config("spark.hadoop.fs.s3a.secret.key", configuration.get('AWS_SECRET_KEY')) \
        .config("spark.hadoop.fs.s3a.aws.credentials.provider",
                "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
        .getOrCreate()

    # adjust the log level to minimize console output
    spark.sparkContext.setLogLevel('WARN')

    vehicle_schema = StructType([
        StructField("id", StringType(), True),
        StructField("deviceId", StringType(), True),
        StructField("timestamp", TimestampType(), True),
        StructField("location", StringType(), True),
        StructField("speed", DoubleType(), True),
        StructField("direction", StringType(), True),
        StructField("make", StringType(), True),
        StructField("model", StringType(), True),
        StructField("year", IntegerType(), True),
        StructField("fuelType", StringType(), True)
      ]
    )

    gps_schema = StructType([
        StructField("id", StringType(), True),
        StructField("deviceId", StringType(), True),
        StructField("timestamp", TimestampType(), True),
        StructField("speed", DoubleType(), True),
        StructField("direction", StringType(), True),
        StructField("vehicleType", StringType(), True)
      ]
    )

    traffic_schema = StructType([
        StructField("id", StringType(), True),
        StructField("deviceId", StringType(), True),
        StructField("cameraId", StringType(), True),
        StructField("location", StringType(), True),
        StructField("timestamp", TimestampType(), True),
        StructField("snapshot", StringType(), True)
      ]
    )

    weather_schema = StructType([
        StructField("id", StringType(), True),
        StructField("deviceId", StringType(), True),
        StructField("location", StringType(), True),
        StructField("timestamp", TimestampType(), True),
        StructField("temperature", DoubleType(), True),
        StructField("weatherCondition", StringType(), True),
        StructField("precipitation", DoubleType(), True),
        StructField("windSpeed", DoubleType(), True),
        StructField("humidity", IntegerType(), True),
        StructField("airQualityIndex", DoubleType(), True)
      ]
    )

    emergency_schema = StructType([
        StructField("id", StringType(), True),
        StructField("deviceId", StringType(), True),
        StructField("incidentId", StringType(), True),
        StructField("type", StringType(), True),
        StructField("timestamp", TimestampType(), True),
        StructField("location", StringType(), True),
        StructField("status", StringType(), True),
        StructField("description", StringType(), True)
      ]
    )

    def read_kafka_topic(topic, schema):
        return (spark.readStream
                .format('kafka')
                .option('kafka.bootstrap.servers', 'broker:29092')
                .option('subscribe', topic)
                .option('startingOffsets', 'earliest')
                .load()
                .selectExpr('CAST(value AS STRING)')
                .select(from_json(col('value'), schema).alias('data'))
                .select('data.*')
                .withWatermark('timestamp', '5 minutes')
                )

    def streamWriter(input: DataFrame, checkpointFolder, output):
        return (input.writeStream
                .format('parquet')
                .option('checkpointLocation', checkpointFolder)
                .option('path', output)
                .outputMode('append')
                .start())

    vehicledf = read_kafka_topic('vehicle_data', vehicle_schema).alias('vehicle')
    gpsdf = read_kafka_topic('gps_data', gps_schema).alias('gps')
    trafficdf = read_kafka_topic('traffic_data', traffic_schema).alias('traffic')
    weatherdf = read_kafka_topic('weather_data', weather_schema).alias('weather')
    emergencydf = read_kafka_topic('emergency_data', emergency_schema).alias('emergency')

    query1 = streamWriter(vehicledf, 's3a://spark-streaming-data-8435/checkpoints/vehicle_data',
                          's3a://spark-streaming-data-8435/data/vehicle_data')
    query2 = streamWriter(gpsdf, 's3a://spark-streaming-data-8435/checkpoints/gps_data',
                          's3a://spark-streaming-data-8435/data/gps_data')
    query3 = streamWriter(trafficdf, 's3a://spark-streaming-data-8435/checkpoints/traffic_data',
                          's3a://spark-streaming-data-8435/data/traffic_data')
    query4 = streamWriter(weatherdf, 's3a://spark-streaming-data-8435/checkpoints/weather_data',
                          's3a://spark-streaming-data-8435/data/weather_data')
    query5 = streamWriter(emergencydf, 's3a://spark-streaming-data-8435/checkpoints/emergency_data',
                          's3a://spark-streaming-data-8435/data/emergency_data')

    query5.awaitTermination()


if __name__ == "__main__":
    main()
