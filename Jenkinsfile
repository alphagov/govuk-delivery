#!/usr/bin/env groovy

REPOSITORY = 'govuk-delivery'

node {

  def govuk = load '/var/lib/jenkins/groovy_scripts/govuk_jenkinslib.groovy'

  try {
    stage('Checkout') {
      checkout scm
    }

    stage("Install packages") {
      sh("rm -rf ./test-venv")
      sh("virtualenv --no-site-packages ./test-venv")
      sh("./test-venv/bin/python -m pip -q install -r requirements-test.txt")
    }

    stage("Test") {
      govuk.setEnvar("GOVUK_ENV", "ci")
      sh("PYTHONPATH=. ./test-venv/bin/python ./test-venv/bin/nosetests")
    }

    stage("Push release tag") {
       govuk.pushTag(REPOSITORY, env.BRANCH_NAME, 'release_' + env.BUILD_NUMBER)
    }

    stage("Deploy on Integration") {
      govuk.deployIntegration(REPOSITORY, env.BRANCH_NAME, 'release', 'deploy')
    }

  } catch (e) {
    currentBuild.result = "FAILED"
    step([$class: 'Mailer',
          notifyEveryUnstableBuild: true,
          recipients: 'govuk-ci-notifications@digital.cabinet-office.gov.uk',
          sendToIndividuals: true])
    throw e
  }
}
