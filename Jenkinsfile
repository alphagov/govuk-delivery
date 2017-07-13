#!/usr/bin/env groovy

REPOSITORY = 'govuk_delivery'
APPLICATION_NAME = 'govuk-delivery'

node {
  def govuk = load '/var/lib/jenkins/groovy_scripts/govuk_jenkinslib.groovy'

  try {
    stage('Checkout') {
      checkout scm
      govuk.cleanupGit()
      govuk.mergeMasterBranch()
    }

    stage('Installing Packages') {
      sh("rm -rf ./test-venv")
      sh("virtualenv --no-site-packages ./test-venv")
      sh("./test-venv/bin/python -m pip -q install -r requirements-test.txt")
    }

    stage('Tests') {
      govuk.setEnvar("GOVUK_ENV", "ci")
      sh("PYTHONPATH=. ./test-venv/bin/python ./test-venv/bin/nosetests")
    }

    if (env.BRANCH_NAME == 'master') {
      stage("Push release tag") {
        repository = "gds/govuk_delivery"
        tag = "release_" + env.BUILD_NUMBER
        git_push = "git push git@github.gds:${repository}.git"
        sshagent(["govuk-ci-ssh-key"]) {
          sh("git tag -a ${tag} -m 'Jenkinsfile tagging with ${tag}'")
          echo "Tagging ${repository} master branch -> ${tag}"
          sh("${git_push} ${tag}")
          echo "Updating ${repository} release branch"
          sh("${git_push} HEAD:release")
        }
      }

      stage('Deploy to Integration') {
        govuk.deployIntegration(APPLICATION_NAME, BRANCH_NAME, 'release', 'deploy')
      }
    }
  } catch (e) {
    currentBuild.result = 'FAILED'
    step([$class: 'Mailer',
          notifyEveryUnstableBuild: true,
          recipients: 'govuk-ci-notifications@digital.cabinet-office.gov.uk',
          sendToIndividuals: true])
    throw e
  }
}
