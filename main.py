import os
from tkinter import *
from tkinter import filedialog as fd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.pyplot import plot, show, xlabel, ylabel, figure, yticks, gcf
from datetime import datetime, timedelta


def get_directory():
    window = Tk()
    window.title("Licence Log Analyser")
    window.config(padx=50, pady=50)
    canvas = Canvas(height=200, width=300)

    log_file_label = Label(text="Select log file.")
    log_file_label.config(font=("Ariel", 14))
    log_file_label.grid(column=0, columnspan=2, row=0, sticky='n', pady=20)

    select_button = Button(text="Select", width=15, command=lambda: select_file(window))
    select_button.grid(column=1, row=1, sticky='e')

    close_button = Button(text="Close", width=15, command=window.destroy)
    close_button.grid(column=0, row=1, sticky='w')

    window.mainloop()


def select_file(window):
    filename = fd.askopenfilename(title="Choose log file", initialdir="/", filetypes=[("log files", "*.log")])
    window.destroy()
    analyse(filename)


def create_df(csv_file):
    # Adds friendly name and formats date for log and denied files. Creates df to pass to other functions.
    csv_file_df = pd.read_csv(csv_file)
    friendly_names = pd.read_csv("reference/ProductNames.csv")

    # join to friendly names
    df = pd.merge(csv_file_df, friendly_names, left_on='product', right_on='Feature Name', how='left')
    df = df.drop('Feature Name', axis=1)
    df["fproduct"] = df["SOLIDWORKS Product"].fillna(df["product"])

    # create datetime column
    df["datetime"] = pd.to_datetime(df['date'] + ' ' + df['time'], format="mixed", dayfirst=True)

    return df

def list_select_products(log_df, denied_df):
    list_products = log_df["fproduct"].unique()

    start_date = log_df["datetime"].min()
    end_date = log_df["datetime"].max()

    window = Tk()
    window.title("Licence Log Analyser")
    window.config(padx=50, pady=50)
    canvas = Canvas(height=200, width=300)

    date_label = Label(text=f"Log Start: {start_date.strftime('%d/%m/%Y %H:%M:%S')}   "
                            f"Log End: {end_date.strftime('%d/%m/%Y %H:%M:%S')}")
    date_label.grid(column=0, row=1, columnspan=3)

    products_label = Label(text=f"Selected products to view:")
    products_label.config(font=("Ariel", 14))
    products_label.grid(column=0, row=0, columnspan=3, sticky='w')

    product_list = Listbox(window, selectmode="multiple", width=50)
    product_list.grid(column=0, row=2, columnspan=3)

    for each_item in range(len(list_products)):
        product_list.insert(END, list_products[each_item])
        product_list.itemconfig(each_item, bg="yellow" if each_item % 2 == 0 else "cyan")

    # add number of denied records for each product (as text below selection list)
    grouped_denied = denied_df.groupby(['fproduct']).size().reset_index(name='denied')
    labels = []

    for index, row in grouped_denied.iterrows():
        new_text = f"{row['fproduct']}: Licence denied {row['denied']} times."
        new_label = Label(text=new_text)
        labels.append(new_label)

    for i in range(len(labels)):
        labels[i].grid(column=0, row=i+3, columnspan=3, sticky='w')

    plot_button = Button(text=f"Plot usage", width=15,
                         command=lambda: plot_licences(log_df, get_selected_products(product_list)))
    plot_button.grid(column=2, row=i+4, sticky='e')

    close_button = Button(text="Close", width=15, command=window.destroy)
    close_button.grid(column=0, row=i+4, stick='w')

    window.mainloop()


def get_selected_products(listbox):
    # find user selected items in listbox and pass as list
    selected_items = []
    for i in listbox.curselection():
        selected_items.append(listbox.get(i))
    return selected_items


def plot_licences(log_df, products):
    # plot selected products on line graph to show usage over time

    # restricted to user selected products
    df_selected = log_df.query(f"fproduct in {products}")

    # pivot table to report on each product on the same plot
    pivot = pd.pivot_table(df_selected, index="datetime", values='licence', columns='fproduct', fill_value=0)
    pivot.to_csv("out.csv")
    pivot = pivot.cumsum().reset_index()
    pivot.to_csv("out_cs.csv")

    plt.figure(figsize=(14, 10))
    for column in pivot.columns[1:]:
        plot(pivot.datetime,
                 pivot[column],
                 linewidth=1,
                 label=pivot[column].name)
        plt.xticks(fontsize=8, rotation=45)
        xlabel("Date/Time")
        ylabel("Licences used")
    plt.legend(fontsize=8)
    plt.show()


def analyse(file):
    log_csv_ext = "_log.csv"                # extension to use for output

    log_lines = []                        # list of lines to write to output csv (per file)
    denied = []
    with open(file, 'r') as log_file:
        lines = log_file.readlines()
        hour = 0
        for line in lines:
            if "Start-Date: " in line:
                date_string = line.split("Start-Date: ")[1].split(" GMT")[0]
                hour = int(date_string[16:18])
                date_string = date_string[:15]
                date = datetime.strptime(date_string, '%a %b %d %Y')
            if "OUT:" in line or "IN:" in line:     # record licences as affect on number of used licences
                if "OUT:" in line:
                    log_direction = 1
                else:
                    log_direction = -1
                log_time = line[:8]
                new_hour = int(log_time[:2])
                if new_hour < hour:                     # crossed into new day, increase date
                    date = date + timedelta(days=1)
                hour = new_hour
                log_user = line.split("@")[0].split(" ")[-1] + "@" + line.split("@")[1].split(" ")[0]
                if "(INACTIVE)" in line:
                    log_reason = "INACTIVE"
                else:
                    log_reason = ""
                log_product = line.split(' "')[1].split('" ')[0]
                log_lines.append({"date": date.strftime('%d/%m/%Y'),
                                  "time": log_time,
                                  "product": log_product,
                                  "licence": log_direction,
                                  "user": log_user})
            if "DENIED" in line:
                denied_time = line[:8]
                denied_user = line.split("@")[0].split(" ")[-1] + "@" + line.split("@")[1].split(" ")[0]
                denied_reason = line.split("  ")[1]
                denied_product = line.split(' "')[1].split('" ')[0]
                denied.append({"date": date.strftime('%d/%m/%Y'),
                                  "time": denied_time,
                                  "product": denied_product,
                                  "reason": denied_reason,
                                  "user": denied_user})

    name_log_csv = file.split('.')[-2] + log_csv_ext

    # delete existing log csv if it exists
    if os.path.isfile(name_log_csv):
        os.remove(name_log_csv)
        print("Delete old log file.")

    # create csv for use with pandas
    with open(name_log_csv, 'a') as log_csv_file:
        print("Creating new log file.")
        log_csv_file.write("date,time,product,licence,user\n")

        for log_line in log_lines:
            log_csv_file.write(f"{log_line['date']},"
                               f"{log_line['time']},"
                               f"{log_line['product']},"
                               f"{log_line['licence']},"
                               f"{log_line['user']}\n")

        print(f"log file updated: {log_csv_file.name}")


    denied_csv = file.split('.')[-2] + "_denied.csv"
    # delete existing denied csv if it exists
    if os.path.isfile(denied_csv):
        os.remove(denied_csv)
        print("Delete old denied file.")

    # create csv for use with pandas
    with open(denied_csv, 'a') as denied_csv_file:
        print("Creating new denied file.")
        denied_csv_file.write("date,time,product,reason,user\n")

        for denied_line in denied:
            denied_csv_file.write(f"{denied_line['date']},"
                               f"{denied_line['time']},"
                               f"{denied_line['product']},"
                               f"{denied_line['reason']},"
                               f"{denied_line['user']}\n")

        print(f"denied file updated: {denied_csv_file.name}")

    log_df = create_df(log_csv_file.name)
    denied_df = create_df(denied_csv_file.name)
    list_select_products(log_df, denied_df)


if __name__ == "__main__":
    get_directory()
