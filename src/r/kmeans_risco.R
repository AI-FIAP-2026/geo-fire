# --- 1. BIBLIOTECAS ---
if (!require("pacman")) install.packages("pacman")
pacman::p_load(ggplot2, cluster)

# --- 2. CARREGAMENTO DOS DADOS ---
args <- commandArgs(trailingOnly = TRUE)
caminho_csv <- ifelse(length(args) >= 1, args[1], "data/firms_com_clima.csv")
df <- read.csv(caminho_csv)

cat("Registros carregados:", nrow(df), "\n")

# --- 3. PRÉ-PROCESSAMENTO ---
# Seleciona features para clustering: coordenadas + FRP + variáveis climáticas
cols_cluster <- c("latitude", "longitude", "frp", "temp_mean", "humidity", "precipitation", "wind_speed")
df_cluster <- na.omit(df[, cols_cluster])

cat("Registros após remoção de NAs:", nrow(df_cluster), "\n")

# Padroniza as variáveis (média 0, desvio 1)
df_scaled <- scale(df_cluster)

# --- 4. K-MEANS (k=3) ---
set.seed(123)
k <- 3
km <- kmeans(df_scaled, centers = k, nstart = 25)

# Adiciona o cluster ao data frame original (sem NAs)
df_cluster$cluster <- as.factor(km$cluster)

# --- 5. SUMÁRIO POR CLUSTER ---
cat("\n--- SUMÁRIO POR CLUSTER (médias) ---\n")
sumario <- aggregate(. ~ cluster, data = df_cluster, FUN = mean)
print(sumario)

cat("\n--- CONTAGEM POR CLUSTER ---\n")
print(table(df_cluster$cluster))

# --- 6. GRÁFICO DE DISPERSÃO (lat x long) ---
p <- ggplot(df_cluster, aes(x = longitude, y = latitude, color = cluster)) +
  geom_point(size = 1.5, alpha = 0.7) +
  scale_color_manual(
    values = c("1" = "#e41a1c", "2" = "#377eb8", "3" = "#4daf4a"),
    name = "Cluster"
  ) +
  labs(
    title = "Zonas de Risco de Queimadas — K-Means Clustering",
    x = "Longitude",
    y = "Latitude"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(hjust = 0.5, face = "bold"),
    legend.position = "bottom"
  )

ggsave("assets/kmeans_clusters.png", plot = p, width = 10, height = 6, dpi = 150)
cat("\nGráfico salvo em: assets/kmeans_clusters.png\n")

# --- 7. CONCLUSÃO ---
cat("\n--- CONCLUSÃO ---\n")
medias <- aggregate(frp ~ cluster, data = df_cluster, FUN = mean)
max_frp <- medias[which.max(medias$frp), ]
cat("Cluster com maior FRP médio:", max_frp$cluster,
    "(FRP médio =", round(max_frp$frp, 2), "MW)\n")

medias_temp <- aggregate(temp_mean ~ cluster, data = df_cluster, FUN = mean)
min_temp <- medias_temp[which.min(medias_temp$temp_mean), ]
cat("Cluster com menor temperatura média:", min_temp$cluster,
    "(temp_mean =", round(min_temp$temp_mean, 2), "°C)\n")

medias_umid <- aggregate(humidity ~ cluster, data = df_cluster, FUN = mean)
min_umid <- medias_umid[which.min(medias_umid$humidity), ]
cat("Cluster com menor umidade:", min_umid$cluster,
    "(humidity =", round(min_umid$humidity, 2), "%)\n")

medias_precip <- aggregate(precipitation ~ cluster, data = df_cluster, FUN = mean)
min_precip <- medias_precip[which.min(medias_precip$precipitation), ]
cat("Cluster com menor precipitação:", min_precip$cluster,
    "(precipitation =", round(min_precip$precipitation, 2), "mm)\n")
