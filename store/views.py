from django.db.models import Count
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, DestroyModelMixin, UpdateModelMixin
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework import status
from .models import Product, Collection, OrderItem, Review, Cart, CartItem, Customer, Order
from .serializers import (
    AddCartItemSerializer,
    CartItemSerializer,
    CartSerializer,
    CollectionSerializer,
    CreateOrderSerializer,
    OrderSerializer,
    ProductSerializer,
    ReviewSerializer,
    UpdateCartItemSerializer,
    CustomerSerializer,
    UpdateOrderSerializer
)
from .filters import ProductFilter
from .pagination import DefaultPagination
from .permissions import FullDjangoModelPermission, IsAdminOrReadOnly, ViewCustomerHistoryPermission


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    # filterset_fields = ['collection_id', 'unit_price']
    filterset_class = ProductFilter
    pagination_class = DefaultPagination
    search_fields = ["title", "description"]
    ordering_fields = ["unit_price", "last_update"]
    permission_classes = [IsAdminOrReadOnly]

    def get_serializer_context(self):
        return {"request": self.request}

    def destroy(self, request, *args, **kwargs):
        if OrderItem.objects.filter(product_id=kwargs["pk"]).count() > 0:
            return Response(
                {
                    "error": "Product cannot be deleted as it is associated with an OrderItem"
                },
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )
        return super().destroy(request, *args, **kwargs)


class CollectionViewSet(ModelViewSet):
    queryset = Collection.objects.annotate(products_count=Count("products")).all()
    serializer_class = CollectionSerializer

    def destroy(self, request, *args, **kwargs):
        if Product.objects.filter(product_id=kwargs["pk"]).count() > 0:
            return Response(
                {"error": "Cannot delete a collection with products"},
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )
        return super().destroy(request, *args, **kwargs)


class ReviewViewSet(ModelViewSet):
    serializer_class = ReviewSerializer

    def get_queryset(self):
        return Review.objects.filter(product_id=self.kwargs["product_pk"])

    def get_serializer_context(self):
        return {"product_id": self.kwargs["product_pk"]}


class CartViewSet(CreateModelMixin, RetrieveModelMixin, DestroyModelMixin, GenericViewSet):
    queryset = Cart.objects.prefetch_related("items__product").all()
    serializer_class = CartSerializer


class CartItemViewSet(ModelViewSet):
    http_method_names = ['get', 'patch', 'post', 'delete']
    
    def get_serializer_class(self):
        if self.request.method == 'POST': 
            return AddCartItemSerializer
        elif self.request.method == 'PATCH':
            return UpdateCartItemSerializer
        return CartItemSerializer
    
    def get_serializer_context(self):
        return {"cart_id" : self.kwargs['cart_pk']}

    def get_queryset(self):
        return CartItem.objects \
                .filter(cart_id = self.kwargs['cart_pk']) \
                .select_related('product')


class CustomerViewSet(ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAdminUser]

    @action(detail=True, permission_classes=[ViewCustomerHistoryPermission])
    def history(self, request, pk):
        return Response("ok")

    @action(detail=False, methods=["GET", "PUT"], permission_classes=[IsAuthenticated])
    def me(self, request):
        customer = Customer.objects.get(
            user_id=request.user.id)
        if request.method == 'GET':
            serializer = CustomerSerializer(customer)
            return Response(serializer.data)
        elif request.method == 'PUT':
            serializer = CustomerSerializer(customer, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)


class OrderViewSet(ModelViewSet):
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.request.method in ["PATCH", "DELETE"]:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = CreateOrderSerializer(
            data=request.data, context={"user_id": self.request.user.id}
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        serializer = OrderSerializer(order)
        return Response(serializer.data)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateOrderSerializer
        elif self.request.method == "PATCH":
            return UpdateOrderSerializer
        return OrderSerializer

    def get_serializer_context(self):
        return {'user_id' : self.request.user.id}

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return Order.objects.all()

        customer_id = Customer.objects.only('id').get(user_id=user.id)
        return Order.objects.filter(customer_id=customer_id)


# collectionlist ka code h yeh pehle wala
# def get(self, request):
#     queryset = Collection.objects.annotate(products_count=Count("products")).all()
#     serializer = CollectionSerializer(queryset, many=True)
#     return Response(serializer.data)

# def post(self, request):
#     serializer = CollectionSerializer(data=request.data)
#     serializer.is_valid(raise_exception=True)
#     serializer.save()
#     return Response(serializer.data, status=status.HTTP_201_CREATED)


# short form above
# class ProductList(APIView):
#     def get(self, request):
#         queryset = Product.ojects.select_related("collection").all()
#         serializer = ProductSerializer(
#             queryset, many = True, context = {"request" : request}
#         )
#         return Response(serializer.data)

#     def post(self, request):
#         serializer = ProductSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()

#         # print(serializer.validated_data)
#        return Response(serializer.data)


# @api_view(["GET", "PUT", "DELETE"])
# def collection_detail(request, pk):
#     collection = get_object_or_404(
#         Collection.objects.annotate(products_count=Count("products")), pk=pk
#     )

#     if request.method == "GET":
#         serializer = CollectionSerializer(collection)
#         return Response(serializer.data)
#     elif request.method == "PUT":
#         serializer = CollectionSerializer(collection, data=request.data)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(serializer.data)
#     elif request.method == "DELETE":
#         if collection.products.count() > 0:
#             return Response(
#                 {"error": "Cannot delete a collection with products"},
#                 status=status.HTTP_405_METHOD_NOT_ALLOWED,
#             )
#         collection.delete()
#         return Response(status=status.HTTP_204_NO_CONTENT)


# class ProductDetail(APIView):
#     def get(self, request, id):
#         product = get_object_or_404(Product, pk=id)
#         serializer = ProductSerializer(product)
#         return Response(serializer.data)

#     def put(self, request, id):
#         product = get_object_or_404(Product, pk=id)
#         serializer = ProductSerializer(product, data=request.data)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(serializer.data, status=status.HTTP_201_CREATED)

#     def delete(self, request, id):
#         product = get_object_or_404(Product, pk=id)
#         print("OrderItem Exists:", product.orderitem_set.exists())
#         if product.orderitem_set.count() > 0:
#             return Response(
#                 {
#                     "error": "Product cannot be deleted as it is associated with an OrderItem"
#                 },
#                 status=status.HTTP_405_METHOD_NOT_ALLOWED,
#             )
#         product.delete()
#         return Response(status=status.HTTP_204_NO_CONTENT)


# try:
#     product = Product.objects.get(pk=id)
#     serializer = ProductSerializer(product)
#     return Response(serializer.data)

# except Product.DoesNotExist:
#     return Response(status = status.HTTP_404_NOT_FOUND)
