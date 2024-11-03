
#%%
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from datetime import datetime, timedelta

# Generate private key for CA
ca_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)

# Create CA certificate
ca_name = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, u"AU"),
    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Queensland"),
    x509.NameAttribute(NameOID.LOCALITY_NAME, u"Brisbane"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Data Models"),
    x509.NameAttribute(NameOID.COMMON_NAME, u"My CA"),
])

ca_cert = x509.CertificateBuilder().subject_name(
    ca_name
).issuer_name(
    ca_name
).public_key(
    ca_key.public_key()
).serial_number(
    x509.random_serial_number()
).not_valid_before(
    datetime.utcnow()
).not_valid_after(
    datetime.utcnow() + timedelta(days=365)
).add_extension(
    x509.BasicConstraints(ca=True, path_length=None), critical=True,
).sign(ca_key, hashes.SHA256())

# Save the CA private key
with open("ca_key.pem", "wb") as f:
    f.write(ca_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ))

# Save the CA certificate
with open("ca_cert.pem", "wb") as f:
    f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

print("CA certificate and key have been created and saved as 'ca_cert.pem' and 'ca_key.pem'.")

# %%
