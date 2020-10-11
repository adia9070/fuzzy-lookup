import os
import logging
import re
import time
import pandas as pd
import redis
import pyarrow as pa
from datetime import timedelta
from flask import Flask, redirect, url_for, render_template , request, flash, send_file, session, g

#User Defined
from fuzzystring import tfidf, send_tfidf_complete_information
#############


r = r = redis.StrictRedis(host='redis-14479.c73.us-east-1-2.ec2.cloud.redislabs.com', port=14479, db=0, password='sLQIFi4OW5E3qbksBF7XmrNSzprx1YwO')
r.set('visitor', 0)

decide_factor = 0

allowed_extension = set(['xls','xlsx','csv'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extension



app = Flask(__name__)
app.config['SECRET_KEY'] = 'd3b7883041c1b79a0995b4afd25ccc99'


@app.route("/")
@app.route('/index')
def index():
	global decide_factor

	visitor = r.get('visitor').decode('utf-8')
	visitor = int(visitor) + 1

	r.set('visitor', visitor)

	session['username'] = visitor
	return render_template('index.html', session_user = session['username'], decide_factor = decide_factor)


@app.route('/upload', methods=['GET','POST'])
def upload():
	global decide_factor

	filename_list = list()
	if request.method == 'POST':

		no_of_file_uploaded = 0
		for file in request.files.getlist('file'):
			if file.filename != '':
				no_of_file_uploaded += 1

		if request.form["filetype"] == "Fuzzy Lookup":
			#Fuzzy Part Begin
			if request.form["filecheck"] == "False":
				if no_of_file_uploaded != 2:
					flash('Upload Both Files')
					return redirect(url_for('index'))
				for count, file in enumerate(request.files.getlist('file')):
					if allowed_file(file.filename):

						filename_list.append(file.filename)
						if count == 0:
							if file.filename.endswith('xlsx'):
								df1 = pd.read_excel(file)
							elif file.filename.endswith('csv'):
								df1 = pd.read_csv(file)
							
							key = str(session['username']) + 'df1'
							context = pa.default_serialization_context()
							r.set(key, context.serialize(df1).to_buffer().to_pybytes(), 900)

						if count == 1:
							if file.filename.endswith('xlsx'):
								df2 = pd.read_excel(file)
							elif file.filename.endswith('csv'):
								df2 = pd.read_csv(file)
							
							key = str(session['username']) + 'df2'
							context = pa.default_serialization_context()
							r.set(key, context.serialize(df2).to_buffer().to_pybytes(), 900)

					else:
						flash("Upload Excel or csv Only")
						return redirect(url_for('index'))
			else:
				if no_of_file_uploaded != 1:
					flash("No File Uploaded")
					return redirect(url_for('index'))

				for count, file in enumerate(request.files.getlist('file')):
					
					if file.filename == '':
						continue

					if allowed_file(file.filename):
						filename_list.append(file.filename) 
						if file.filename.endswith('xlsx'):
							df_single = pd.read_excel(file)
						elif file.filename.endswith('csv'):
							df_single = pd.read_csv(file)
						filename_list.append(file.filename)

						key = str(session['username']) + 'df'
						context = pa.default_serialization_context()
						r.set(key, context.serialize(df_single).to_buffer().to_pybytes())

					else:
						flash("Upload xlsx or xls Only")
						return redirect(url_for('index'))

			if request.form["filecheck"] == "False":

				filename1 = filename_list[0]
				filename2 = filename_list[1]

			else:

				df1 = df_single
				df2 = df_single
				filename1 = filename_list[0]
				filename2 = filename_list[0]
		

			column_name1 = df1.columns.values
			column_name2 = df2.columns.values
			filecheck = request.form["filecheck"]

			key = str(session['username']) + 'filecheck'
			r.set(key, filecheck, 900)
			
			return render_template('fuzzstring.html', column1 = column_name1, column2 = column_name2, filename= filename_list, session_user = session['username'], decide_factor = decide_factor)

	return redirect(url_for('index'))	
		
@app.route('/fuzzstring', methods=['GET','POST'])
def fuzzstring():
	global decide_factor
	context = pa.default_serialization_context()

	filecheck = r.get(str(session['username'])+'filecheck')
	if filecheck.decode('utf-8') == 'True':
		df1 = context.deserialize(r.get(str(session['username'])+'df'))
		df2 = context.deserialize(r.get(str(session['username'])+'df'))
	else:
		df1 = context.deserialize(r.get(str(session['username'])+'df1'))
		df2 = context.deserialize(r.get(str(session['username'])+'df2'))
	

	if request.method == 'POST':
		username = session['username']
		threshold_list = request.form.getlist('range') 
		request_at1 = request.form.getlist('employee')
		request_at2 = request.form.getlist('vendor')

		index_column_one = request_at1[0]
		index_column_two = request_at2[0]

		reference_id = list()
		score = list()
		header = ["ReferenceID"]
		summarys = df1[index_column_one].tolist()

		for count, (fuzzycol1, fuzzycol2, threshold) in enumerate(zip(request_at1[1:], request_at2[1:], threshold_list)):
			result = tfidf(df1, df2, index_column_one, index_column_two, fuzzycol1, fuzzycol2, int(threshold), filecheck.decode('utf-8'))
			complete_result = send_tfidf_complete_information(df1, df2, result, index_column_one, index_column_two, fuzzycol1, fuzzycol2)
			
			dataframe_rid = result["Refernce_id_one"].tolist()
			reference_id.append(dataframe_rid)	
			dataframe_score = result["similarity_score"].tolist()
			score.append(dataframe_score)
		
		r.delete(str(session['username'])+'df')
		r.delete(str(session['username'])+'df1')
		r.delete(str(session['username'])+'df2')
		r.delete(str(session['username'])+'filecheck')

		return complete_result.to_html()

	return redirect(url_for('index'))
	

if __name__ == '__main__':
	app.run(debug=False)
