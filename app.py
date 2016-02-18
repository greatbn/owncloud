import owncloud

from flask import Flask,session,render_template,redirect,url_for,request,jsonify

from flask.ext.bootstrap import Bootstrap

import datetime,json,urllib,os

#address = os.environ.get('ADDRESS')
address = 'http://172.16.69.240/owncloud'
username = None
password = None

list_files = None
current_path = None
app = Flask(__name__)
Bootstrap(app)

SECRET_KEY = "owncloud"

app.config.from_object(__name__)
conn = None
error = None
list_share = []
def connect_owncloud( address, username, password):
    
    try:
       client = owncloud.Client(address) 
       client.login(username,password)
    except owncloud.HTTPResponseError as e:
           return e.status_code
    return client


@app.route('/login',methods=["GET","POST"])
def login():
    global error
    error = None
    if request.method == 'POST':
        global username
        global password
        username = request.form['username']
        password = request.form['password']
        global conn
        conn = connect_owncloud(address,username,password)
        if isinstance(conn,int):
            if conn == 401:
                error = "Username or password not correct"
                return render_template("login.html",error = error)
            elif conn == 404:
                error = "Server not found" 
                return render_template("login.html",error =error)
        session['logged_in'] = True
        return redirect(url_for("view",path="/"))
    return render_template("login.html",error=error)

@app.route('/logout')
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))


@app.route("/")
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    else:
        return redirect(url_for("view",path="/"))

@app.route('/action',methods=['POST','GET'])
def action():
    action = request.args.get('action')
    file_name = request.args.get('file')
    path = request.args.get('path')
    print file_name
    if action == 'delete':
        conn.delete(file_name)
        return redirect(url_for('view',path=path))
    if action == 'download':
        conn.get_file(file_name)
        return redirect(url_for('view',path=path))
    if request.method == 'POST':
        new_name = request.form['newname']
        print new_name
        conn.move(file_name,path+'/'+new_name)
        print 'ok'
        return redirect(url_for('view',path=path))

@app.route('/new/<action>',methods=['GET','POST'])
def new(action):
    if request.method =='POST':
        if action == 'upload':
            file_name = request.files['file']
            print file_name.__dict__
            print file_name
            conn.put_file(current_path,file_name)
            return redirect(url_for('view',path = current_path))


@app.route('/share/changepermission',methods=['POST'])
def change_perms():
    if not request.json:
        abort(400)
    data = request.json
    conn.delete_share(int(data['share_id']))
    perms = int(data['permissions'],2)
    if 'user' in data:
        conn.share_file_with_user(str(data['file_name']),str(data['user']),perms=perms)
    if 'group' in data:
        conn.share_file_with_group(str(data['file_name']),str(data['group']),perms=perms)
    return redirect(url_for("share",file_name =data['file_name'][1:] ))

@app.route('/share/<path:file_name>',methods=['GET','POST'])
def share(file_name):
    file_name = '/'+file_name
    # global list_share
    global error
    error = None
  
    if request.method == 'POST':
        
        if request.form['share_with'] == 'user':
            user = request.form['user']
            
            try:
                conn.get_user(user)
                conn.share_file_with_user(file_name,user)
                print 'ok'
                return redirect(url_for('share',file_name=file_name[1:]))
            except:
                error = "User not exist"
                return render_template("share.html",error = error,file_name=file_name,list_share = list_share)
        elif request.form['share_with'] == 'group':
            group = request.form['user']
            print group
            if conn.group_exists(group) :
                conn.share_file_with_group(file_name,group)
                print 'ok'
                return redirect(url_for('share',file_name=file_name[1:]))
            else:
                error = "Group not exist"
                return render_template("share.html" ,error = error,file_name=file_name,list_share = list_share)
    if request.args.get('share') == 'link':
        conn.share_file_with_link(file_name)
        return redirect(url_for('share',file_name = file_name[1:]))
    elif request.args.get('share') == 'dellink':
        conn.delete_share(int(request.args.get('id')))
        return redirect(url_for('share',file_name = file_name[1:]))
    if conn.is_shared(file_name):
        share_info = conn.get_shares(file_name)
        info = {}
        global list_share
        list_share= []
        for share in share_info:
            info = share.share_info
            if info['share_type'] == 3:
                info['']
            info['exp'] = share.get_expiration()
            info['permissions'] = '{0:05b}'.format(int(info['permissions']))
            list_share.append(info.copy())
        
        return render_template("share.html",list_share = list_share,file_name=file_name,error = error)
    else:
        list_share = None
        return render_template("share.html",list_share = None,file_name= file_name,error = error)

    


@app.route('/file')
def view():
    path = request.args.get('path')
    
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    else:
        global list_file
        list_files = conn.list(path)
        File_Detail =  {}
        List = []
        global current_path
        current_path = list_files[0].get_path().split(list_files[0].get_name())[0]
        for File in list_files:

            File_Detail['content-type'] = File.get_content_type()
            File_Detail['last-modified'] = datetime.datetime.now() - File.get_last_modified()
            File_Detail['path'] = File.path
            File_Detail['parent-dir'] = File.get_path()
            File_Detail['is_dir'] = File.is_dir()
            File_Detail['file-type'] =str(File.file_type)
            File_Detail['name'] = File.get_name()
            File_Detail['etag'] = File.get_etag()
            File_Detail['shared'] = conn.is_shared(File_Detail['path'])
            if File_Detail['is_dir']:
                File_Detail['size'] = int(json.loads(json.dumps(dict(File.attributes)))['{DAV:}quota-used-bytes'])
            else:
                File_Detail['size'] = File.get_size()

            List.append(File_Detail.copy())
        print List
        return render_template("index.html",List=List)
if __name__=='__main__':
    app.run(host='0.0.0.0',port='5000')