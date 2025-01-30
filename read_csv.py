import csv

def validate_credentials(salesman_id, password):
    try:
        with open("salesmen.csv", mode="r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row["salesman_id"] == salesman_id and row["password"] == password:
                    return row["name"]  # Return name if credentials are valid
        return None  # Invalid credentials
    except FileNotFoundError:
        print("Error: salesmen.csv file not found!")
        return None

# Test the function
salesman_id = input("Enter Salesman ID: ")
password = input("Enter Password: ")
name = validate_credentials(salesman_id, password)

if name:
    print(f"Welcome, {name}!")
else:
    print("Invalid credentials!")
