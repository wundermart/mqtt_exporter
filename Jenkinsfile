// only create cronjob for "master" branch
def generateYaml() {

            def binding = [
                'IMAGE': 'gcr.io/kaniko-project/executor:debug',
                'SECRET_NAME': 'credential-secret'
            ]

    def yamlTemplate = """
    apiVersion: v1
    kind: Pod
    spec:
        containers:
        - name: kaniko
          image: "${binding.IMAGE}"
          imagePullPolicy: Always
          command:
          - sleep
          args:
          - 1000
          volumeMounts:
              - name: credential-secret
                mountPath: /secret
          env:
            - name: GOOGLE_APPLICATION_CREDENTIALS
              value: /secret/credential-secret.json
        volumes:
            - name: credential-secret
              secret:
                secretName: "${binding.SECRET_NAME}"
    """
            return yamlTemplate
}
def generateYaml2() {
            def yamlTemplate2 = """
            apiVersion: v1
            kind: Secret
            metadata:
                name: credential-secret
                namespace: jenkins 
            type: Opaque
            data:
                credential-secret.json: "${GC_KEY_CONTENT}"
            """
            return yamlTemplate2   

}
def dockerBuildAndPushTools() {
        container(name: 'kaniko') {
            // Image Tags
            GIT_BRANCH_TAG = "eu.gcr.io/custom-hold-271312/mqttv2"
            LATEST_TAG = "${GIT_BRANCH_TAG}:latest"
            echo 'Run Kaniko build'
            sh("""
            /kaniko/executor \
                --log-format=text \
                --context=. \
                --dockerfile=./Dockerfile \
                --destination=$LATEST_TAG \
                --cache=true \
                --cache-ttl=24h \
                --cache-repo=eu.gcr.io/custom-hold-271312/mqttv2/cache \
            """)
        }
}


pipeline {
    agent any
      environment {
        GC_KEY_CONTENT = ''
    }
    triggers { cron('30 2 * * *') }
    stages {
        stage("Create secret") {
            agent any
            steps {
                script {
                        //deploy the secret

                        withCredentials([file(credentialsId: 'development-cluster-credentials', variable: 'GC_KEY')]) {
                            def GC_KEY_CONTENT_PRE = readFile file: GC_KEY
                            GC_KEY_CONTENT = GC_KEY_CONTENT_PRE.bytes.encodeBase64().toString()
                            def secretYaml = generateYaml2()
                            writeFile(file: 'secret.yaml', text: secretYaml)
                            sh("cat secret.yaml")
                            echo "Login to GCloud"
                            sh("gcloud auth activate-service-account --key-file=${GC_KEY}")
                            echo "Set Project name"
                            sh("gcloud container clusters get-credentials devops --region europe-west4 --project wundermart-erp-devops")
                            sh "kubectl apply -f secret.yaml"
                        }
                }
            }
        }
        stage('Submit Build') {
            parallel {
                stage("built mqtt") {
                    agent {
                            kubernetes {
                                yaml generateYaml() //kaniko
                            }
                        }
                    steps {
                        script {
                                //build the image
                                dockerBuildAndPushTools()
                        }
                    }
                    
                }

            }      
        }
    }
    post {
        regression {
            slackSend channel: 'notifications', color: 'danger', message: "mqtt images Docker image build regressed from success to failure!"
        }
        success {
            slackSend channel: 'notifications', message: "mqtt images built successfully."
        }
    }
}
