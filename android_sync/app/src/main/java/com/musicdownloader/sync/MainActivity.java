package com.musicdownloader.sync;

import android.app.*;
import android.os.*;
import android.content.*;
import android.database.Cursor;
import android.net.Uri;
import android.provider.DocumentsContract;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.io.*;
import java.net.*;
import java.util.*;

public class MainActivity extends Activity {
    EditText url; TextView status; Uri tree; final int PICK=7;
    android.content.SharedPreferences prefs;
    public void onCreate(Bundle b) { super.onCreate(b); prefs=getSharedPreferences("sync",0); tree=Uri.parse(prefs.getString("tree",""));
        LinearLayout box=new LinearLayout(this); box.setOrientation(LinearLayout.VERTICAL); box.setPadding(28,28,28,28);
        TextView title=new TextView(this); title.setText("Music Downloader Sync"); title.setTextSize(24); box.addView(title);
        TextView help=new TextView(this); help.setText("Pega el enlace zrok del PC (incluye ?token=...). Elige una vez la carpeta Música y sincroniza solo las novedades."); box.addView(help);
        url=new EditText(this); url.setHint("https://...zrok.../?token=..."); url.setSingleLine(); url.setText(prefs.getString("url","")); box.addView(url);
        Button folder=new Button(this); folder.setText("Elegir carpeta Música"); folder.setOnClickListener(v->pickFolder()); box.addView(folder);
        Button sync=new Button(this); sync.setText("SINCRONIZAR CANCIONES NUEVAS"); sync.setOnClickListener(v->runSync()); box.addView(sync);
        status=new TextView(this); status.setPadding(0,20,0,0); box.addView(status); setContentView(box); }
    void pickFolder(){ startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION|Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION),PICK); }
    protected void onActivityResult(int r,int c,Intent d){super.onActivityResult(r,c,d); if(r==PICK&&c==RESULT_OK){tree=d.getData(); getContentResolver().takePersistableUriPermission(tree,d.getFlags()&(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION)); prefs.edit().putString("tree",tree.toString()).apply(); status.setText("Carpeta guardada.");}}
    void runSync(){ final String raw=url.getText().toString().trim(); if(raw.isEmpty()||tree==null||tree.toString().isEmpty()){status.setText("Indica el enlace zrok y elige la carpeta Música.");return;} prefs.edit().putString("url",raw).apply(); status.setText("Consultando biblioteca del PC..."); new Thread(()->{try{Uri parsed=Uri.parse(raw); final String base=parsed.getScheme()+"://"+parsed.getAuthority(); final String token=parsed.getQueryParameter("token"); if(token==null||token.isEmpty())throw new IOException("El enlace no contiene token de sincronización"); JSONObject m=getJson(base+"/sync/manifest?token="+URLEncoder.encode(token,"UTF-8")); JSONArray files=m.getJSONArray("files"); int done=0,skip=0; for(int i=0;i<files.length();i++){JSONObject f=files.getJSONObject(i);String path=f.getString("path"); long size=f.getLong("size"); if(localSize(path)==size){skip++;continue;} download(base+"/sync/file?token="+URLEncoder.encode(token,"UTF-8")+"&path="+URLEncoder.encode(path,"UTF-8"),path); done++; final int n=done, s=skip; runOnUiThread(()->status.setText("Descargadas "+n+" nuevas. Ya existentes: "+s));} final int d=done,s=skip; runOnUiThread(()->status.setText("Terminada: "+d+" nuevas, "+s+" ya estaban."));}catch(Exception e){runOnUiThread(()->status.setText("Error: "+e.getMessage()));}}).start();}
    JSONObject getJson(String u)throws Exception{HttpURLConnection c=(HttpURLConnection)new URL(u).openConnection();c.setConnectTimeout(15000);c.setReadTimeout(30000);if(c.getResponseCode()!=200)throw new IOException("HTTP "+c.getResponseCode());return new JSONObject(read(c.getInputStream()));}
    void download(String u,String path)throws Exception{HttpURLConnection c=(HttpURLConnection)new URL(u).openConnection();c.setConnectTimeout(15000);c.setReadTimeout(120000);if(c.getResponseCode()!=200)throw new IOException("HTTP "+c.getResponseCode());Uri parent=tree;String[] parts=path.split("/");for(int i=0;i<parts.length-1;i++)parent=dir(parent,parts[i]);Uri file=DocumentsContract.createDocument(getContentResolver(),parent,"audio/mpeg",parts[parts.length-1]);if(file==null)throw new IOException("No se pudo crear "+path);try(InputStream in=c.getInputStream();OutputStream out=getContentResolver().openOutputStream(file,"w")){byte[] b=new byte[65536];int n;while((n=in.read(b))>0)out.write(b,0,n);}}
    Uri dir(Uri parent,String name)throws Exception{Uri found=null;Cursor q=getContentResolver().query(DocumentsContract.buildChildDocumentsUriUsingTree(parent,DocumentsContract.getDocumentId(parent)),new String[]{DocumentsContract.Document.COLUMN_DOCUMENT_ID,DocumentsContract.Document.COLUMN_DISPLAY_NAME,DocumentsContract.Document.COLUMN_MIME_TYPE},null,null,null);if(q!=null){while(q.moveToNext())if(name.equals(q.getString(1))&&DocumentsContract.Document.MIME_TYPE_DIR.equals(q.getString(2)))found=DocumentsContract.buildDocumentUriUsingTree(tree,q.getString(0));q.close();}return found!=null?found:DocumentsContract.createDocument(getContentResolver(),parent,DocumentsContract.Document.MIME_TYPE_DIR,name);}
    long localSize(String path)throws Exception{String[] p=path.split("/");Uri parent=tree;for(int i=0;i<p.length-1;i++){parent=dirExisting(parent,p[i]);if(parent==null)return -1;}Cursor q=getContentResolver().query(DocumentsContract.buildChildDocumentsUriUsingTree(parent,DocumentsContract.getDocumentId(parent)),new String[]{DocumentsContract.Document.COLUMN_DISPLAY_NAME,DocumentsContract.Document.COLUMN_SIZE},null,null,null);long size=-1;if(q!=null){while(q.moveToNext())if(p[p.length-1].equals(q.getString(0)))size=q.isNull(1)?-1:q.getLong(1);q.close();}return size;}
    Uri dirExisting(Uri parent,String name)throws Exception{Cursor q=getContentResolver().query(DocumentsContract.buildChildDocumentsUriUsingTree(parent,DocumentsContract.getDocumentId(parent)),new String[]{DocumentsContract.Document.COLUMN_DOCUMENT_ID,DocumentsContract.Document.COLUMN_DISPLAY_NAME,DocumentsContract.Document.COLUMN_MIME_TYPE},null,null,null);Uri r=null;if(q!=null){while(q.moveToNext())if(name.equals(q.getString(1))&&DocumentsContract.Document.MIME_TYPE_DIR.equals(q.getString(2)))r=DocumentsContract.buildDocumentUriUsingTree(tree,q.getString(0));q.close();}return r;}
    String read(InputStream in)throws Exception{StringBuilder s=new StringBuilder();byte[]b=new byte[8192];int n;while((n=in.read(b))>0)s.append(new String(b,0,n,"UTF-8"));return s.toString();}
}
