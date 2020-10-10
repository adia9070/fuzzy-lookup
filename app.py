import os
import re
import time
import pandas as pd
from datetime import timedelta
from flask import Flask, redirect, url_for, render_template , request, flash, send_file, session, g

#User Defined
from fuzzystring import tfidf, send_tfidf_complete_information
#############


file_upload_by_user = {}
visitor = 0
decide_factor = 0

allowed_extension = set(['xls','xlsx','csv'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extension



app = Flask(__name__)
app.config['SECRET_KEY'] = 'd3b7883041c1b79a0995b4afd25ccc99'


@app.route("/")
@app.route('/index')
def index():
	global visitor
	global decide_factor

	visitor = visitor + 1

	session['username'] = visitor
	return render_template('index.html', session_user = session['username'], decide_factor = decide_factor)


@app.route('/upload', methods=['GET','POST'])
def upload():

	global decide_factor
	global file_upload_by_user

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
						if count == 1:
							if file.filename.endswith('xlsx'):
								df2 = pd.read_excel(file)
							elif file.filename.endswith('csv'):
								df2 = pd.read_csv(file)
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
			print(session['username'])
			file_upload_by_user[session['username']] = [df1, df2, filecheck]

			return render_template('fuzzstring.html', column1 = column_name1, column2 = column_name2, filename= filename_list, session_user = session['username'], decide_factor = decide_factor)
	
	return redirect(url_for('index'))	
		
@app.route('/fuzzstring', methods=['GET','POST'])
def fuzzstring():

	print("fuzzy got the session", session['username'])
	global decide_factor
	global file_upload_by_user

	df1 = file_upload_by_user[session['username']][0]
	df2 = file_upload_by_user[session['username']][1]
	filecheck = file_upload_by_user[session['username']][2]

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
			result = tfidf(df1, df2, index_column_one, index_column_two, fuzzycol1, fuzzycol2, int(threshold), filecheck)
			complete_result = send_tfidf_complete_information(df1, df2, result, index_column_one, index_column_two, fuzzycol1, fuzzycol2)
			
			dataframe_rid = result["Refernce_id_one"].tolist()
			reference_id.append(dataframe_rid)	
			dataframe_score = result["similarity_score"].tolist()
			score.append(dataframe_score)

		file_upload_by_user.pop(session['username'],None)
		print(file_upload_by_user)

		selected_columns = len(reference_id)
		return complete_result.to_html()

	return redirect(url_for('index'))
	

if __name__ == '__main__':
   app.run(debug=True)
