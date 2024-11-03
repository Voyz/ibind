## Quickstart

1. Clone the repository to your local machine.
2. Install project dependencies by running: `pip install -r requirements.txt`.
3. Copy your private signature and encryption keys into the project.
4. Create a .env file in the project root directory. The .env file should contain the following fields:

  - **CONSUMER_KEY**: The consumer key configured during the onboarding process. This uniquely identifies the project in the IBKR ecosystem.
  - **SIGNATURE_KEY_FP**: The path to the private signature key.
  - **ENCRYPTION_KEY_FP**: The path to the private encryption key.
  - **REALM**: The realm. This is generally set to "limited_poa", however should be set to "test_realm" when using the TESTCONS consumer key.
  - **DH_PRIME**: The hex representation of the Diffie-Hellman prime.
  - **DH_GENERATOR**: The Diffie-Hellman generator value. This is usually 2.