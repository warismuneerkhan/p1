from django.shortcuts import render,redirect
from .models import orderdetail, pet,customer,cart,order,payment
from django.http import HttpResponse
from django.views.generic import DeleteView,ListView,CreateView,UpdateView,DetailView
from django.db.models import Q
from django.contrib.auth.hashers import make_password,check_password
from datetime import date
from django.core.mail import EmailMessage
from django.conf import settings
import razorpay



# Create your views here.
class petview(ListView):
    model = pet
    template_name= 'pet_list.html'
    context_object_name ='petobj'

    def get_context_data(self, **kwargs):
        data = self.request.session['sessionvalue']
        context = super().get_context_data(**kwargs)
        context['session'] = data
        return context


def search(request):
    if request.method =="POST":
        session = request.session['sessionvalue']
        searchdata = request.POST.get('searchquery')
        petobj = pet.objects.filter(Q(name__icontains =searchdata)|Q(breed__icontains =searchdata)|Q(species__icontains =searchdata))
        return render(request,'pet_list.html',{'petobj':petobj,'session':session})
    

def register(request):
    if request.method =="GET":
        return render(request,'register.html')
    elif request.method =="POST":
        firstname = request.POST.get('name')
        email =  request.POST.get('email')
        phoneno =  request.POST.get('phoneno')
        password = request.POST.get('password')
        epassword = make_password(password)

        custobj = customer(name=firstname,password=epassword,email=email,phoneno=phoneno)
        custobj.save()
        return redirect('../login/')
    


def login(request):
    if request.method == "GET":
        return render(request, 'login.html')
    elif request.method == "POST":
        username = request.POST.get('user')
        print(username)
        password = request.POST.get('password')
        print(password)

        cust = customer.objects.filter(email = username)
        if cust:
            custobj = customer.objects.get(email=username)

            flag = check_password(password,custobj.password)

            if flag:
                request.session['sessionvalue'] = custobj.email
                return redirect('../PetView/')
            else:
                return render(request,'login.html',{'msg':'Incorrect username and Password'})
            
        else:
            return render(request,'login.html',{'msg':'Incorrect username and Password'})
            
        
        

def addtocart(request):
    productid = request.POST.get('productid')
    custsession = request.session['sessionvalue'] #email of customer
    custobj = customer.objects.get(email = custsession) #fetch record from database table using email
    custid = custobj.id #fetch customer id using customer object
    pobj = pet.objects.get(id = productid)

    flag = cart.objects.filter(cid = custobj.id,pid = pobj.id)
    if flag:
        cartobj = cart.objects.get(cid = custobj.id,pid = pobj.id)
        cartobj.quantity = cartobj.quantity +1
        cartobj.totalamount = pobj.price * cartobj.quantity
        cartobj.save()
    else:
        cartobj = cart(cid = custobj,pid = pobj,quantity = 1,totalamount = pobj.price*1)
        cartobj.save()

    return redirect('../PetView/')


def viewcart(request):
    custsession = request.session['sessionvalue'] #email of customer
    custobj = customer.objects.get(email = custsession) 
    cartobj = cart.objects.filter(cid = custobj.id)

    return render(request,'cart.html',{'cartobj':cartobj,'session':custsession})

def cq(request):
    cemail = request.session['sessionvalue']
    pid = request.POST.get('pid')
    custobj = customer.objects.get(email = cemail)
    pobj = pet.objects.get(id = pid)
    cartobj = cart.objects.get(cid = custobj.id,pid=pobj.id)

    if request.POST.get('changequantitybtn')=='+':
        cartobj.quantity = cartobj.quantity + 1
        cartobj.totalamount = cartobj.quantity * pobj.price
        cartobj.save()

    elif request.POST.get('changequantitybtn')=='-':
        if cartobj.quantity == 1:
            cartobj.delete()
        else :
            cartobj.quantity = cartobj.quantity - 1
            cartobj.totalamount = cartobj.quantity * pobj.price
            print(cartobj.totalamount)
            cartobj.save()

    return redirect('../viewcart')

def summary(request):
    custsession = request.session["sessionvalue"]
    custobj = customer.objects.get(email = custsession)
    cartobj = cart.objects.filter(cid = custobj.id)
    print(cartobj)
    totalbill = 0
    for i in cartobj:
        totalbill = i.totalamount + totalbill

    return render(request, "summary.html", {'session': custsession, 'cartobj': cartobj, 'totalbill': totalbill})

def placeorder(request):
    fn = request.POST.get('fn')
    ln = request.POST.get('ln')
    address = request.POST.get('address')
    city = request.POST.get('city')
    state = request.POST.get('state')
    pincode = request.POST.get('pincode')
    phoneno = request.POST.get('phoneno')

    datev = date.today()
    # print(datev.date)
    orderobj = order(firstname = fn, lastname = ln, address = address, city = city, state = state, pincode = pincode, phoneno = phoneno, orderdate = datev, orderstatus = 'pending')
    orderobj.save()

    ono = str(orderobj.id) + str(datev).replace('-', '')
    orderobj.ordernumber = ono
    orderobj.save()

    custsession = request.session["sessionvalue"]
    custobj = customer.objects.get(email = custsession)
    cartobj = cart.objects.filter(cid = custobj.id)
    totalbill = 0
    for i in cartobj:
        totalbill = i.totalamount + totalbill



    sm = EmailMessage('order placed', 'order placed from pet store application. Total bill for your order is '+str(totalbill),to=['wk3118276@gmail.com'])
    sm.send()

     # authorize razorpay client with API Keys.
    razorpay_client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
 
 

    currency = 'INR'
    amount = 20000  # Rs. 200
 
    # Create a Razorpay Order
    razorpay_order = razorpay_client.order.create(dict(amount=amount,
     currency=currency,
     payment_capture='0'))
 
    # order id of newly created order.
    razorpay_order_id = razorpay_order['id']
    callback_url = '../PetView'
 
    # we need to pass these details to frontend.
    context = {}
    context['razorpay_order_id'] = razorpay_order_id
    context['razorpay_merchant_key'] = settings.RAZORPAY_KEY_ID
    context['razorpay_amount'] = amount
    context['currency'] = currency
    context['callback_url'] = callback_url
    return render(request, "payment.html", { 'orderobj': orderobj, 'session': custsession, 'cartobj': cartobj, 'totalbill': totalbill, 'context':context})


class petdetail(DetailView):
    model = pet
    template_name = 'pet_details.html'
    context_object_name = 'i'

def paymentsuccess(request):
    orderid = request.GET.get('order_id')
    tid = request.GET.get('payment_id')
    request.session['sessionvalue']=request.GET.get('session')
    usersession = request.session['sessionvalue']
    #print(usersession)
    customerobj = customer.objects.get(email=usersession)
    #print(customerobj.id)
    cartobj = cart.objects.filter(cid = customerobj.id)

    orderobj = order.objects.get(ordernumber = orderid)
    paymentobj = payment(transactionid = tid, paymentstatus='paid',customerid=customerobj,oid = orderobj)
    paymentobj.save()
    for i in cartobj:
        orderdetailobj = orderdetail(paymentid = paymentobj,ordernumber = orderid, productid = i.pid,customerid = customerobj,quantity = i.quantity,totalprice = i.totalamount)
        orderdetailobj.save()
        i.delete()
    
    return render(request,'paymentsuccesful.html',{'session':usersession,'payobj':paymentobj})

def logout(request):
    del(request.session['sessionvalue'])
    return redirect('../login/')