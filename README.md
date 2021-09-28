## Software Reengineering lab on MSR
In this repo you will find the course content for lecture Mining Repositories for the course Software Re-engineering at the University of Antwerp, Belgium

### 1 - Prepare to run the script 

<ul>
    <li>Clone the repo in git bash or terminal or cmd</li>
</ul>

```python
git clone https://github.com/johnxu21/sre2020-21.git
```
<li>Open it in your favourite editor</li>

<li>In the directory src you find a script CollectFiles.py </li>
<li>Update the script as below with your info </li>

On line 52 **repo = 'kuyesu/sre'** supply repo as the example below from your github with username and repo

Edit **lstTokens** with your own generated token, __to generate new token, from, go to **settings** and to **developer setting** then on **gerate new token**__ 

### 2(Linux) - Running the script on linux

To run the script on Linux

First give a execution permission using the command below

```python
sudo chmod u+x script.sh
```
Now run the script

```python
sudo ./script.sh
```
### 2(Windows) - Running the script on Windows

All you have to do is just execute the **script.bat** file

```python
script.bat
```