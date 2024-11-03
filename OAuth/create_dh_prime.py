

#%%
from Crypto.PublicKey import DSA
from Crypto.IO import PEM
from Crypto.PublicKey import RSA
from Crypto.Util.number import long_to_bytes, bytes_to_long
from Crypto.PublicKey import DSA 
from Crypto.Util.asn1 import DerSequence

def create_dh_prime():
    # Generate DH parameters (using DSA for simplicity)
    key = DSA.generate(2048)

    # Extract the prime number
    p = key.p

    # Create PEM structure
    der_data = key.export_key(format='DER')
    pem_data = PEM.encode(der_data, 'DH PARAMETERS')

    # Save to a PEM file
    with open('dhparam_dummy.pem', 'wb') as pem_file:
        pem_file.write(pem_data.encode('ascii'))

    print("Dummy DH parameters saved as dhparam_dummy.pem")

def extract_dh_prime(filename):
    # Load the PEM file
    with open(filename, 'rb') as pem_file:
        pem_data = pem_file.read()

    # Decode the PEM file
    der_data = PEM.decode(pem_data.decode('ascii'))[0]

    # Load the DH parameters
    dh_parameters = DSA.import_key(der_data)

    # Extract the prime number
    prime = dh_parameters.p
    return prime

def pem_to_integer(pem_file_path): 
    with open(pem_file_path, 'r') as pem_file: 
        pem_data = pem_file.read() 
    key = RSA.import_key(pem_data) 
    prime = key.n 
    
    return prime

def pem_to_dh_prime(pem_file_path): 
    with open(pem_file_path, 'rb') as pem_file: 
        pem_data = pem_file.read() 

    dsa_key = DSA.import_key(pem_data) 
    prime = dsa_key.p 
    return prime

#%%
# Create DH prime and save to PEM file
# create_dh_prime()
filename=r'C:\Users\hughj\OneDrive\Files\Trading\InteractiveBrokers\dhparam.pem'
# Extract DH prime from PEM file
dh_prime = extract_dh_prime(filename=filename)
print(f"Extracted Prime Number: {dh_prime}")

#%%

pem_file_path=r'C:\Users\hughj\OneDrive\Files\Trading\InteractiveBrokers\dhparam.pem'

prime_integer = pem_to_integer(pem_file_path) 
print(f"Prime as integer: {prime_integer}")
# %%

pem_file_path = r'C:\Users\hughj\OneDrive\Files\Trading\InteractiveBrokers\dhparam.pem'
prime_integer = pem_to_dh_prime(pem_file_path) 
print(f"Prime as integer: {prime_integer}")

#%%

from Crypto.PublicKey import DSA
from Crypto.Util.asn1 import DerSequence

def pem_to_dh_prime(pem_file_path):
    with open(pem_file_path, 'rb') as pem_file:
        pem_data = pem_file.read()

    dsa_key = DSA.import_key(pem_data)
    prime = dsa_key.p
    return prime

pem_file_path = r'C:\Users\hughj\OneDrive\Files\Trading\InteractiveBrokers\dhparam.pem'
prime_integer = pem_to_dh_prime(pem_file_path)
print(f"Prime as integer: {prime_integer}")

#%%

from cryptography.hazmat.primitives.asymmetric import dh
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_parameters

def pem_to_dh_prime(pem_file_path):
    with open(pem_file_path, 'rb') as pem_file:
        pem_data = pem_file.read()
    
    parameters = load_pem_parameters(pem_data)
    prime = parameters.parameter_numbers().p
    return prime

pem_file_path = r'C:\Users\hughj\OneDrive\Files\Trading\InteractiveBrokers\dhparam.pem'
prime_integer = pem_to_dh_prime(pem_file_path)
print(f"Prime as integer: {prime_integer}")


# %%
