# NOTE: Make sure you have your project files in the ./project directory
# Will run the autograder and place the results in ./results/results.json
run:
	docker run --rm \
		-v ./project:/autograder/submission \
		-v ./results:/autograder/results \
		sockets-are-cool \
		/autograder/run_autograder && cat results/results.json

# In case you want to run the autograder manually, use interactive
interactive:
	(docker ps | grep sockets-are-cool && \
	docker exec -it sockets-are-cool bash) || \
	docker run --rm --name sockets-are-cool -it \
		-v ./project:/autograder/submission \
		-v ./results:/autograder/results \
		sockets-are-cool bash

build:
	docker build -t sockets-are-cool -f autograder/Dockerfile .

publish:
	docker tag sockets-are-cool eado0/sockets-are-cool
	docker push eado0/sockets-are-cool
