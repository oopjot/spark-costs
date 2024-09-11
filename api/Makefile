psql:
	docker-compose exec -it database psql -U lolek -d spark_costs

reset-database:
	docker-compose down database
	docker-compose up -d database
	docker-compose restart api worker

api-shell:
	docker-compose run --rm -it api python -ic "import database; import model; import crud; db = next(database.get_db())"

worker-shell:
	docker-compose run --rm -it worker python -ic "import worker"

