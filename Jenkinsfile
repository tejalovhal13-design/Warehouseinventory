pipeline {
    agent any

    environment {
        DOCKER_HUB_REPO = 'tejal1319/warehouse-inventory'
        DOCKER_CRED_ID  = 'dockerhub-credentials'
        CONTAINER_NAME  = 'warehouse_app'
        APP_PORT        = '8000'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                sh "docker build -t ${DOCKER_HUB_REPO}:latest -t ${DOCKER_HUB_REPO}:${BUILD_NUMBER} ."
            }
        }

        stage('Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(credentialsId: DOCKER_CRED_ID, usernameVariable: 'USER', passwordVariable: 'PASS')]) {
                    sh "echo \$PASS | docker login -u \$USER --password-stdin"
                    sh "docker push ${DOCKER_HUB_REPO}:latest"
                    sh "docker push ${DOCKER_HUB_REPO}:${BUILD_NUMBER}"
                }
            }
        }

        stage('Deploy Container') {
            steps {
                sh "docker stop ${CONTAINER_NAME} || true"
                sh "docker rm ${CONTAINER_NAME} || true"
                sh "docker run -d -p ${APP_PORT}:${APP_PORT} --name ${CONTAINER_NAME} ${DOCKER_HUB_REPO}:latest"
            }
        }
    }

    post {
        always {
            sh "docker logout"
        }
    }
}