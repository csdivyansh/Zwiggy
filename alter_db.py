import sqlite3

conn = sqlite3.connect('restaurantmenu.db')
cursor = conn.cursor()

# Execute a query to retrieve data from a table
# cursor.execute("UPDATE User SET role = 'owner' WHERE username = 'csdiv'")
cursor.execute("Select * from user")
rows = cursor.fetchall()

# Print the results
for row in rows:
    print(row)

# Close the connection
conn.commit()
conn.close()
