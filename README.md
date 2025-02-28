# crocoquant

##Trading Bot with Docker

This project is a simple trading bot that uses the Interactive Brokers (IBKR) API for executing trades and retrieving market data. The bot runs inside a Docker container for consistent setup and environment management.

##Table of Contents

    Project Overview
    Prerequisites
    Installation
    Running the Bot
    Updating Dependencies
    Stopping the Docker Container
    License

##Project Overview

This project implements a basic trading bot designed to interact with Interactive Brokers' API. The bot can fetch market data and make simple trades based on pre-configured strategies. The bot is containerized with Docker to simplify deployment and environment consistency.

##Prerequisites

Before getting started, ensure you have the following installed:

a) Docker: Install Docker
b) Interactive Brokers Account: You will need a live or paper trading account with Interactive Brokers. Install Trader Workstation (TWS) or IB Gateway to access the IBKR API.

##Installation

1. Clone the Repository

Clone the repository to your local machine:

    git clone https://github.com/Adudzinski/crocoquant
    cd crocoquant

2. Build the Docker Container

Build the Docker image by running the following command in your project folder:

    docker build -t crocoquant .

This will create a Docker image containing all necessary dependencies for the bot.


##Running the Bot

1. Start the Docker Container

After building the image, run the bot inside a Docker container:

    docker run -d --name crocoquant-container crocoquant

This command will start the container in detached mode. The bot should now be running inside the container.

2. Check Logs (Optional)

You can check the logs of the running bot with:

    docker logs -f trading-bot-container

##Updating Dependencies

If you add or update any Python dependencies, follow these steps to update your Docker container:

1. Install New Dependencies Locally Install the required dependencies with:

    pip install <new-dependency-name>

2. Update requirements.txt After installing the new dependencies, update the requirements.txt by running:

    pipreqs . --force

(If pipreqs is not installed do: pip install pipreqs) 

3. Rebuild the Docker Image Rebuild the Docker image to include the new dependencies:

    docker build -t trading-bot .

4. Restart the Docker Container After rebuilding the image, restart the container with the new dependencies:

    docker stop crocoquant-container
    docker rm crocoquant-container
    docker run -d --name crocoquant-container crocoquant

##Stopping the Docker Container

To stop the running bot, use the following command:

    docker stop trading-bot-container

To completely remove the container:

    docker rm trading-bot-container


