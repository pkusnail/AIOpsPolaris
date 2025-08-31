#!/bin/bash

echo "停止所有容器..."
docker-compose down

echo "启动容器并应用CPU隔离..."

# 手动启动每个容器并应用cpuset-cpus限制
echo "启动MySQL (CPU 0)..."
docker run -d --name aiops-mysql \
  --cpuset-cpus="0" \
  --cpus="1.0" \
  --network aiopspolaris_aiops-network \
  -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=aiops123 \
  -e MYSQL_DATABASE=aiops \
  -e MYSQL_USER=aiops_user \
  -e MYSQL_PASSWORD=aiops_pass \
  -v aiopspolaris_mysql_data:/var/lib/mysql \
  -v "$(pwd)/docker/mysql/init.sql:/docker-entrypoint-initdb.d/init.sql" \
  --restart unless-stopped \
  mysql:8.0

echo "启动Redis (CPU 3)..."
docker run -d --name aiops-redis \
  --cpuset-cpus="3" \
  --cpus="1.0" \
  --network aiopspolaris_aiops-network \
  -p 6379:6379 \
  -v aiopspolaris_redis_data:/data \
  --restart unless-stopped \
  redis:7.2-alpine redis-server --appendonly yes --requirepass aiops123

# 等待基础服务启动
sleep 10

echo "检查基础服务状态..."
docker ps | grep -E "(mysql|redis)"

echo ""
echo "CPU隔离配置完成！每个容器现在只能看到分配给它的CPU核心。"
echo "检查容器CPU可见性："
echo "MySQL (应该只看到1个CPU): $(docker exec aiops-mysql nproc 2>/dev/null || echo '容器未启动')"
echo "Redis (应该只看到1个CPU): $(docker exec aiops-redis nproc 2>/dev/null || echo '容器未启动')"