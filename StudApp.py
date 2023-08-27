from flask import Flask, render_template, request
from pymysql import connections
import os
import boto3
from config import *

app = Flask(__name__)

# DBHOST = os.environ.get("DBHOST")
# DBPORT = os.environ.get("DBPORT")
# DBPORT = int(DBPORT)
# DBUSER = os.environ.get("DBUSER")
# DBPWD = os.environ.get("DBPWD")
# DATABASE = os.environ.get("DATABASE")

bucket= custombucket
region= customregion
table= customtable

db_conn = connections.Connection(
    host= customhost,
    port=3306,
    user= customuser,
    password= custompass,
    db= customdb
    
)
output = {}
table = 'students';

@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('Addstu.html')

@app.route("/about", methods=['POST'])
def about():
    return render_template('www.intellipaat.com');
@app.route("/addstu", methods=['POST'])
def Addstu():
    stu_id = request.form['emp_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    degree = request.form['degree']
    cgpa = request.form['location']
    stu_image_file = request.files['stu_image_file']
  
    insert_sql = "INSERT INTO students VALUES (%s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    if stu_image_file.filename == "":
        return "Please select a file"

    try:
        
        cursor.execute(insert_sql,(stu_id, first_name, last_name, degree, cgpa))
        db_conn.commit()
        stud_name = "" + first_name + " " + last_name
        # Uplaod image file in S3 #
        stu_image_file_name_in_s3 = "stu_id-"+str(stu_id) + "_image_file"
        s3 = boto3.resource('s3')

        
        
        try:
            print("Data inserted in MySQL RDS... uploading image to S3...")
            s3.Bucket(custombucket).put_object(Key=stu_image_file_name_in_s3, Body=stu_image_file)
            bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

            object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                stu_image_file_name_in_s3)

            # Save image file metadata in DynamoDB #
            print("Uploading to S3 success... saving metadata in dynamodb...")
        
            
            try:
                dynamodb_client = boto3.client('dynamodb', region_name= customregion )
                dynamodb_client.put_item(
                 TableName= customtable,
                    Item={
                     'stuid': {
                          'N': stu_id
                      },
                      'image_url': {
                            'S': object_url
                        }
                    }
                )

            except Exception as e:
                program_msg = "Flask could not update DynamoDB table with S3 object URL"
                return str(e)
        
        except Exception as e:
            return str(e)

    finally:
        cursor.close()

    print("all modification done...")
    return render_template('AddstuOutput.html', name=stu_name)

@app.route("/getstu", methods=['GET', 'POST'])
def Getstu():
    return render_template("Getstu.html")


@app.route("/fetchdata", methods=['GET','POST'])
def FetchData():
    stu_id = request.form['stu_id']

    output = {}
    select_sql = "SELECT stu_id, first_name, last_name, degree, cgpa from students where stu_id=%s"
    cursor = db_conn.cursor()

    try:
        cursor.execute(select_sql,(stu_id))
        result = cursor.fetchone()

        output["stu_id"] = result[0]
        print('EVERYTHING IS FINE TILL HERE')
        output["first_name"] = result[1]
        output["last_name"] = result[2]
        output["degree"] = result[3]
        output["cgpa"] = result[4]
        print(output["stu_id"])
        dynamodb_client = boto3.client('dynamodb', region_name=customregion)
        try:
            response = dynamodb_client.get_item(
                TableName= customtable ,
                Key={
                    'stuid': {
                        'N': str(stu_id)
                    }
                }
            )
            image_url = response['Item']['image_url']['S']

        except Exception as e:
            program_msg = "Flask could not update DynamoDB table with S3 object URL"
            return render_template('addstuerror.html', errmsg1=program_msg, errmsg2=e)

    except Exception as e:
        print(e)

    finally:
        cursor.close()

    return render_template("GetstuOutput.html", id=output["stu_id"], fname=output["first_name"],
                           lname=output["last_name"], deg=output["degree"], percentage=output["cgpa"],
                           image_url=image_url)

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=80,debug=True)
