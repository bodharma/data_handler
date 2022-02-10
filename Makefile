.PHONY: help install-dependencies create-artifact-bucket deploy-stn-craft-scraper

ARTIFACT_BUCKET := test

help: ## This help
	@grep -E -h "^[a-zA-Z_-]+:.*?## " $(MAKEFILE_LIST) \
	  | sort \
	  | awk -v width=36 'BEGIN {FS = ":.*?## "} {printf "\033[36m%-*s\033[0m %s\n", width, $$1, $$2}'


install-dependencies: ## Install pipenv and dependencies
	@echo '*** installing dependencies ***'
	pip3 install pipenv
	pipenv install --dev
	@echo '*** dependencies installed ***'


create-artifact-bucket:  ## Create bucket to upload stack to
	aws s3 mb s3://${ARTIFACT_BUCKET}


deploy-stn-craft-scraper:
	@echo '*** building ***'
	sam build --use-container
	sam package --s3-bucket eu-central-1-scraper-data --output-template-file packaged.yaml --region eu-central-1
	@echo '*** deploying ***'
	sam deploy --template-file /Users/blesi/dev/web_scraper/stn-craft-scraper-lambda/packaged.yaml --stack-name scraper --region eu-central-1 --capabilities CAPABILITY_IAM
	@echo '*** deployed ***'