## Software Reengineering lab on MSR
In this repo you will find the course content for lecture Mining Repositories for the course Software Re-engineering at the University of Antwerp, Belgium

**NOTE:** To make a successfull excution, you need to be connected to internet
### 1 - Prepare to run the script 

<ul>
    <li>Clone the repo in git bash or terminal or cmd</li>
</ul>

```python
git clone https://github.com/johnxu21/sre2020-21.git
```
<ul>
<li>Open it in your favourite editor</li>

<li>In the directory <span style="weight: 800">src</span> you find a script <span>CollectFiles.py</span> </li>
<li>Update the script as below with your info </li>
</ul>
<ul>
<li>On line 52 **repo = 'kuyesu/sre'** supply repo as the example below from your github with username and repo</li>
</ul>
<ul><li>Edit **lstTokens** with your own generated token, to generate new token, from, go to **settings** and to **developer setting** then on **gerate new token**</li></ul>

### 2 - Running the script on linux (Linux/Mac)

To run the script on Linux

First give a execution permission using the command below

```python
sudo chmod u+x script.sh
```
Now run the script

```python
sudo ./script.sh
```
### 2 - Running the script on Windows (Windows) 

All you have to do is just execute the **script.bat** file

```python
script.bat
```