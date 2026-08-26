from django.shortcuts import render
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from datetime import timedelta
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes

from bus.models import Bus
from routes.models import Route, RouteStop
from schedule.models import Schedule
from booking.models import Booking, BookingSeat
from hiace.models import Hiace, HiaceRoute, HiaceSchedule, HiaceBooking, HiaceBookingSeat,HiaceRouteStop


class DashboardView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Check if user is a driver/operator
        if user.role != 'D':
            return Response(
                {'error': 'Access denied. Only drivers can access this endpoint.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Get all buses for this operator
            buses = Bus.objects.filter(operator=user, status='ACTIVE')
            bus_ids = buses.values_list('id', flat=True)
            
            # Get all hiace for this operator
            hiaces = Hiace.objects.filter(operator=user, status='ACTIVE')
            hiace_ids = hiaces.values_list('id', flat=True)

            # Get routes for this operator's vehicles
            bus_routes = Route.objects.filter(operator=user, status='ACTIVE')
            hiace_routes = HiaceRoute.objects.filter(operator=user, status='ACTIVE')
            
            # Today's date range
            today = timezone.now().date()
            today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
            today_end = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.max.time()))

            # Current time
            now = timezone.now()

            # Get today's schedules
            today_bus_schedules = Schedule.objects.filter(
                route__bus__in=buses,
                departure_datetime__range=[today_start, today_end],
                status='ACTIVE'
            )
            
            today_hiace_schedules = HiaceSchedule.objects.filter(
                route__in=hiace_routes,
                departure_datetime__range=[today_start, today_end],
                status='ACTIVE'
            )

            # Get active trips (currently in progress)
            active_bus_schedules = Schedule.objects.filter(
                route__bus__in=buses,
                departure_datetime__lte=now,
                arrival_datetime__gte=now,
                status='ACTIVE'
            )
            
            active_hiace_schedules = HiaceSchedule.objects.filter(
                route__in=hiace_routes,
                departure_datetime__lte=now,
                arrival_datetime__gte=now,
                status='ACTIVE'
            )

            # Get upcoming trips (next 24 hours)
            upcoming_start = now
            upcoming_end = now + timedelta(days=1)
            
            upcoming_bus_schedules = Schedule.objects.filter(
                route__in=bus_routes,
                departure_datetime__range=[upcoming_start, upcoming_end],
                status='ACTIVE'
            ).exclude(
                departure_datetime__lte=now
            )
            
            upcoming_hiace_schedules = HiaceSchedule.objects.filter(
                route__in=hiace_routes,
                departure_datetime__range=[upcoming_start, upcoming_end],
                status='ACTIVE'
            ).exclude(
                departure_datetime__lte=now
            )

            # Today's booked seats count
            today_bus_bookings = Booking.objects.filter(
                schedule__in=today_bus_schedules,
                booking_status='PAID'
            )
            today_hiace_bookings = HiaceBooking.objects.filter(
                schedule__in=today_hiace_schedules,
                booking_status='PAID'
            )
            
            today_booked_seats_bus = BookingSeat.objects.filter(
                booking__in=today_bus_bookings
            ).count()
            
            today_booked_seats_hiace = HiaceBookingSeat.objects.filter(
                booking__in=today_hiace_bookings
            ).count()
            
            today_total_booked_seats = today_booked_seats_bus + today_booked_seats_hiace
            
            # Total earnings (all time)
            result = Booking.objects.filter(
                schedule__route__bus__in=buses,
                booking_status="PAID",
            ).aggregate(
                total_amount=Sum("total_amount"),
                platform_amount=Sum("platform_amount"),
            )

            bus_earnings = (result["total_amount"] or 0) - (result["platform_amount"] or 0)

          
            
            result = HiaceBooking.objects.filter(
                schedule__route__in=hiace_routes,
                booking_status="PAID",
            ).aggregate(
                total_amount=Sum("total_amount"),
                platform_amount=Sum("platform_amount"),
            )

            hiace_earnings = (result["total_amount"] or 0) - (result["platform_amount"] or 0)
            
            total_earnings = float(bus_earnings) + float(hiace_earnings)

            # Today's earnings
            # Bus earnings
            bus_result = Booking.objects.filter(
                schedule__in=today_bus_schedules,
                booking_status="PAID",
                created_at__range=[today_start, today_end],
            ).aggregate(
                total_amount=Sum("total_amount"),
                platform_amount=Sum("platform_amount"),
            )

            today_bus_earnings = (
                (bus_result["total_amount"] or 0)
                - (bus_result["platform_amount"] or 0)
            )

            # Hiace earnings
            hiace_result = HiaceBooking.objects.filter(
                schedule__in=today_hiace_schedules,
                booking_status="PAID",
                created_at__range=[today_start, today_end],
            ).aggregate(
                total_amount=Sum("total_amount"),
                platform_amount=Sum("platform_amount"),
            )

            today_hiace_earnings = (
                (hiace_result["total_amount"] or 0)
                - (hiace_result["platform_amount"] or 0)
            )
            
            today_earnings = float(today_bus_earnings) + float(today_hiace_earnings)

            # Total trips completed
            completed_bus_trips = Schedule.objects.filter(
                route__in=bus_routes,
                status='COMPLETED'
            ).count()
            
            completed_hiace_trips = HiaceSchedule.objects.filter(
                route__in=hiace_routes,
                status='COMPLETED'
            ).count()
            
            total_trips_completed = completed_bus_trips + completed_hiace_trips

            # Today's trips
            today_bus_trips = today_bus_schedules.count()
            today_hiace_trips = today_hiace_schedules.count()
            today_total_trips = today_bus_trips + today_hiace_trips

            # Average rating (if you have a rating field)
            # This is a placeholder - you can add a rating field to bookings
            avg_rating = 4.5  # Replace with actual rating calculation

            # Vehicle counts
            total_buses = buses.count()
            total_hiaces = hiaces.count()
            total_vehicles = total_buses + total_hiaces

            # Active vehicles
            active_buses = buses.filter(status='ACTIVE').count()
            active_hiaces = hiaces.filter(status='ACTIVE').count()
            active_vehicles = active_buses + active_hiaces

            # Upcoming trips count
            upcoming_trips = upcoming_bus_schedules.count() + upcoming_hiace_schedules.count()

            # Active trips count
            active_trips = active_bus_schedules.count() + active_hiace_schedules.count()

            # Response data
            data = {
                'stats': {
                    'total_vehicles': total_vehicles,
                    'total_buses': total_buses,
                    'total_hiaces': total_hiaces,
                    'active_vehicles': active_vehicles,
                    'total_trips_completed': total_trips_completed,
                    'today_trips': today_total_trips,
                    'active_trips': active_trips,
                    'upcoming_trips': upcoming_trips,
                    'today_booked_seats': today_total_booked_seats,
                    'total_earnings': round(total_earnings, 2),
                    'today_earnings': round(today_earnings, 2),
                    'avg_rating': round(avg_rating, 1),
                },
                'today_schedules': {
                    'bus': today_bus_schedules.count(),
                    'hiace': today_hiace_schedules.count(),
                    'total': today_total_trips,
                },
                'upcoming_trips_details': {
                    'bus': upcoming_bus_schedules.count(),
                    'hiace': upcoming_hiace_schedules.count(),
                    'total': upcoming_trips,
                },
                'active_trips_details': {
                    'bus': active_bus_schedules.count(),
                    'hiace': active_hiace_schedules.count(),
                    'total': active_trips,
                },
                'earnings': {
                    'total': round(total_earnings, 2),
                    'today': round(today_earnings, 2),
                    'bus': round(bus_earnings, 2),
                    'hiace': round(hiace_earnings, 2),
                },
                'vehicles': {
                    'bus': {
                        'total': total_buses,
                        'active': active_buses,
                    },
                    'hiace': {
                        'total': total_hiaces,
                        'active': active_hiaces,
                    },
                }
            }

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DriverTripsView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        if user.role != 'D':
            return Response(
                {'error': 'Access denied. Only drivers can access this endpoint.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Get all buses and hiaces for this operator
            buses = Bus.objects.filter(operator=user)
            hiaces = Hiace.objects.filter(operator=user)
            
            bus_ids = buses.values_list('id', flat=True)
            hiace_ids = hiaces.values_list('id', flat=True)

            # Get routes
            bus_routes = Route.objects.filter(bus__in=buses, status='ACTIVE')
            hiace_routes = HiaceRoute.objects.filter(hiace__in=hiaces, status='ACTIVE')

            trips = []

            # Get bus schedules
            if bus_routes.exists():
                bus_schedules = Schedule.objects.filter(
                    route__in=bus_routes,
                    status='ACTIVE'
                ).select_related(
                    'route', 
                    'route__source_city', 
                    'route__destination_city', 
                    'route__bus'
                )
                
                # Process bus schedules
                for schedule in bus_schedules:
                    booked_seats = BookingSeat.objects.filter(
                        booking__schedule=schedule,
                        booking__booking_status__in=['PAID', 'CONFIRMED']
                    ).count()
                    
                    total_seats = schedule.route.bus.total_seats
                    
                    # Get passengers
                    bookings = Booking.objects.filter(
                        schedule=schedule,
                        booking_status__in=['PAID', 'CONFIRMED']
                    )
                    
                    passengers = []
                    for booking in bookings:
                        seats = BookingSeat.objects.filter(booking=booking)
                        for seat in seats:
                            passengers.append({
                                'id': booking.id,
                                'name': booking.customer.fullName,
                                'seat': seat.seat.seat_number,
                            })

                    trips.append({
                        'id': schedule.id,
                        'route': f"{schedule.route.source_city.name} → {schedule.route.destination_city.name}",
                        'from': schedule.route.source_city.name,
                        'to': schedule.route.destination_city.name,
                        'departure': schedule.departure_datetime.isoformat(),
                        'arrival': schedule.arrival_datetime.isoformat(),
                        'date': schedule.departure_datetime.date().isoformat(),
                        'status': self.get_trip_status(schedule),
                        'vehicle': schedule.route.bus.bus_name,
                        'vehicleNumber': schedule.route.bus.bus_number,
                        'vehicleType': 'bus',
                        'bookedSeats': booked_seats,
                        'totalSeats': total_seats,
                        'availableSeats': total_seats - booked_seats,
                        'passengers': passengers,
                    })

            # Get hiace schedules
            if hiace_routes.exists():
                hiace_schedules = HiaceSchedule.objects.filter(
                    route__in=hiace_routes,
                    route__operator=user,
                    status='ACTIVE'
                ).select_related(
                    'route', 
                    'route__source_city', 
                    'route__destination_city', 
                    'route__hiace'
                )
                
                # Process hiace schedules
                for schedule in hiace_schedules:
                    booked_seats = HiaceBookingSeat.objects.filter(
                        booking__schedule=schedule,
                        booking__booking_status__in=['PAID', 'CONFIRMED']
                    ).count()
                    
                    total_seats = schedule.route.hiace.total_seats
                    
                    # Get passengers
                    bookings = HiaceBooking.objects.filter(
                        schedule=schedule,
                        booking_status__in=['PAID', 'CONFIRMED']
                    )
                    
                    passengers = []
                    for booking in bookings:
                        seats = HiaceBookingSeat.objects.filter(booking=booking)
                        for seat in seats:
                            passengers.append({
                                'id': booking.id,
                                'name': booking.customer.fullName,
                                'seat': seat.seat.seat_number,
                            })

                    trips.append({
                        'id': schedule.id,
                        'route': f"{schedule.route.source_city.name} → {schedule.route.destination_city.name}",
                        'from': schedule.route.source_city.name,
                        'to': schedule.route.destination_city.name,
                        'departure': schedule.departure_datetime.isoformat(),
                        'arrival': schedule.arrival_datetime.isoformat(),
                        'date': schedule.departure_datetime.date().isoformat(),
                        'status': self.get_trip_status(schedule),
                        'vehicle': schedule.route.hiace.hiace_name,
                        'vehicleNumber': schedule.route.hiace.hiace_number,
                        'vehicleType': 'hiace',
                        'bookedSeats': booked_seats,
                        'totalSeats': total_seats,
                        'availableSeats': total_seats - booked_seats,
                        'passengers': passengers,
                    })

            # Sort trips by departure
            trips.sort(key=lambda x: x['departure'])

            # Apply status filter
            status_filter = request.query_params.get('status')
            if status_filter:
                trips = [t for t in trips if t['status'] == status_filter]

            # If no trips found, return demo data for testing
            if not trips:
                return Response(self.get_demo_trips(user), status=status.HTTP_200_OK)

            return Response(trips, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Error fetching trips: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_trip_status(self, schedule):
        """
        Determine the status of a trip
        """
        now = timezone.now()
        
        if schedule.arrival_datetime < now:
            return 'completed'
        elif schedule.departure_datetime <= now <= schedule.arrival_datetime:
            return 'active'
        else:
            return 'upcoming'

    def get_demo_trips(self, user):
        """Return demo trips for testing"""
        now = timezone.now()
        
        return [
            {
                'id': 1,
                'route': 'Kathmandu → Pokhara',
                'from': 'Kathmandu',
                'to': 'Pokhara',
                'departure': (now + timedelta(hours=1)).isoformat(),
                'arrival': (now + timedelta(hours=6, minutes=30)).isoformat(),
                'date': now.date().isoformat(),
                'status': 'upcoming',
                'vehicle': 'Sajha Bus',
                'vehicleNumber': 'BA 1 KA 1234',
                'vehicleType': 'bus',
                'bookedSeats': 25,
                'totalSeats': 40,
                'availableSeats': 15,
                'passengers': [
                    {
                        'id': 1,
                        'name': 'Rahul Sharma',
                        'seat': 'A1'
                    },
                    {
                        'id': 2,
                        'name': 'Sita Giri',
                        'seat': 'A2'
                    }
                ]
            },
            {
                'id': 2,
                'route': 'Pokhara → Kathmandu',
                'from': 'Pokhara',
                'to': 'Kathmandu',
                'departure': (now + timedelta(hours=3)).isoformat(),
                'arrival': (now + timedelta(hours=8, minutes=30)).isoformat(),
                'date': now.date().isoformat(),
                'status': 'upcoming',
                'vehicle': 'Sajha Hiace',
                'vehicleNumber': 'BA 1 KA 5678',
                'vehicleType': 'hiace',
                'bookedSeats': 8,
                'totalSeats': 12,
                'availableSeats': 4,
                'passengers': []
            },
            {
                'id': 3,
                'route': 'Butwal → Kathmandu',
                'from': 'Butwal',
                'to': 'Kathmandu',
                'departure': (now - timedelta(hours=2)).isoformat(),
                'arrival': (now + timedelta(hours=4, minutes=30)).isoformat(),
                'date': now.date().isoformat(),
                'status': 'active',
                'vehicle': 'Lumbini Express',
                'vehicleNumber': 'BA 2 KA 5678',
                'vehicleType': 'bus',
                'bookedSeats': 32,
                'totalSeats': 40,
                'availableSeats': 8,
                'passengers': [
                    {
                        'id': 3,
                        'name': 'Hari Poudel',
                        'seat': 'B1'
                    },
                    {
                        'id': 4,
                        'name': 'Gita Adhikari',
                        'seat': 'B2'
                    }
                ]
            }
        ]


class DriverTripDetailView(views.APIView):
    """
    Get detailed information about a specific trip
    Supports both Bus and Hiace schedules
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, trip_id):
        user = request.user
        
        # Debug logs
        print(f"=== DriverTripDetailView called ===")
        print(f"User: {user} (ID: {user.id})")
        print(f"Trip ID: {trip_id}")
        print(f"User Role: {user.role}")
        
        # Check if user is a driver/operator
        if user.role != 'D':
            return Response(
                {'error': 'Access denied. Only drivers can access this endpoint.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            trip = None
            trip_type = None
            
            # Get all buses and hiaces belonging to this driver
            user_buses = Bus.objects.filter(operator=user).values_list('id', flat=True)
            user_hiaces = Hiace.objects.filter(operator=user).values_list('id', flat=True)
            
            print(f"User buses: {list(user_buses)}")
            print(f"User hiaces: {list(user_hiaces)}")
            
            # Check bus schedules
            if user_buses:
                try:
                    bus_schedule = Schedule.objects.select_related(
                        'route',
                        'route__source_city',
                        'route__destination_city',
                        'route__bus',
                        'route__operator'
                    ).get(
                        id=trip_id,
                        route__bus__in=user_buses
                    )
                    trip = bus_schedule
                    trip_type = 'bus'
                    print(f"Found bus schedule: {bus_schedule.id} - {bus_schedule.route}")
                except Schedule.DoesNotExist:
                    print(f"No bus schedule found for trip {trip_id}")

            # If not found, check hiace schedules
            if not trip and user_hiaces:
                try:
                    hiace_schedule = HiaceSchedule.objects.select_related(
                        'route',
                        'route__source_city',
                        'route__destination_city',
                        'route__hiace',
                        'route__operator'
                    ).get(
                        id=trip_id,
                        route__hiace__in=user_hiaces
                    )
                    trip = hiace_schedule
                    trip_type = 'hiace'
                    print(f"Found hiace schedule: {hiace_schedule.id} - {hiace_schedule.route}")
                except HiaceSchedule.DoesNotExist:
                    print(f"No hiace schedule found for trip {trip_id}")
            
            if not trip:
                # Check if schedule exists but belongs to another operator
                bus_exists = Schedule.objects.filter(id=trip_id).exists()
                hiace_exists = HiaceSchedule.objects.filter(id=trip_id).exists()
                
                if bus_exists or hiace_exists:
                    return Response(
                        {'error': f'Trip with ID {trip_id} exists but belongs to another operator'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Return demo data for testing
                return self.get_demo_trip_response(trip_id, user)

            print(f"Trip found! Type: {trip_type}")
            
            # Build response based on trip type
            if trip_type == 'bus':
                return self.build_bus_trip_response(trip, user)
            else:
                return self.build_hiace_trip_response(trip, user)

        except Exception as e:
            print(f"Error fetching trip details: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def build_bus_trip_response(self, schedule, user):
        route = schedule.route
        bus = route.bus
        
        # Get booked seats
        booked_seats = BookingSeat.objects.filter(
            booking__schedule=schedule,
            booking__booking_status__in=['PAID', 'CONFIRMED']
        )
        
        # Get passengers
        passengers = []
        for seat in booked_seats:
            booking = seat.booking
            passengers.append({
                'id': booking.id,
                'name': booking.customer.fullName,
                'seatNumber': seat.seat.seat_number,
                'bookingId': booking.booking_number,
                'status': 'confirmed' if booking.booking_status == 'CONFIRMED' else 'checked_in',
                'phone': getattr(booking.customer, 'phone', None),
                'email': booking.customer.email,
            })

        # Get stops
        stops = RouteStop.objects.filter(route=route).order_by('stop_order')
        stops_data = []
        for stop in stops:
            stops_data.append({
                'name': stop.city.name,
                'time': (schedule.departure_datetime + stop.arrival_offset).strftime('%I:%M %p'),
                'type': 'boarding' if stop.is_boarding else 'dropping',
            })

        # Get earnings
        bookings = Booking.objects.filter(
            schedule=schedule,
            booking_status__in=['PAID', 'CONFIRMED']
        )
        total_earnings = bookings.aggregate(total=Sum('total_amount'))['total'] or 0
        platform_fee = float(total_earnings) * 0.10
        driver_earnings = float(total_earnings) - platform_fee

        # Get status
        now = timezone.now()
        if schedule.arrival_datetime < now:
            status = 'completed'
        elif schedule.departure_datetime <= now <= schedule.arrival_datetime:
            status = 'active'
        else:
            status = 'upcoming'

        # Get amenities
        amenities = []
        if bus.wifi: amenities.append('WiFi')
        if bus.charging: amenities.append('Charging')
        if bus.ac: amenities.append('AC')
        if hasattr(bus, 'tv') and bus.tv: amenities.append('TV')

        return Response({
            'id': schedule.id,
            'route': f"{route.source_city.name} → {route.destination_city.name}",
            'from': route.source_city.name,
            'to': route.destination_city.name,
            'departureDate': schedule.departure_datetime.isoformat(),
            'departureTime': schedule.departure_datetime.isoformat(),
            'arrivalDate': schedule.arrival_datetime.isoformat(),
            'arrivalTime': schedule.arrival_datetime.isoformat(),
            'duration': self.format_duration(schedule.arrival_datetime - schedule.departure_datetime),
            'vehicle': bus.bus_name,
            'vehicleNumber': bus.bus_number,
            'vehicleType': bus.bus_type,
            'totalSeats': bus.total_seats,
            'availableSeats': bus.total_seats - booked_seats.count(),
            'bookedSeats': booked_seats.count(),
            'fare': schedule.fare if hasattr(schedule, 'fare') else None,
            'status': status,
            'driver': {
                'name': route.operator.fullName,
                'phone': getattr(route.operator, 'phone', 'N/A'),
                'rating': 4.8,
            },
            'passengers': passengers,
            'earnings': {
                'total': float(total_earnings),
                'platformFee': float(platform_fee),
                'driverEarnings': float(driver_earnings),
            },
            'amenities': amenities,
            'stops': stops_data,
        })

    def build_hiace_trip_response(self, schedule, user):
        route = schedule.route
        hiace = route.hiace
        
        # Get booked seats
        booked_seats = HiaceBookingSeat.objects.filter(
            booking__schedule=schedule,
            booking__booking_status__in=['PAID', 'CONFIRMED']
        )
        
        # Get passengers
        passengers = []
        for seat in booked_seats:
            booking = seat.booking
            passengers.append({
                'id': booking.id,
                'name': booking.customer.fullName,
                'seatNumber': seat.seat.seat_number,
                'bookingId': booking.booking_number,
                'status': 'confirmed' if booking.booking_status == 'CONFIRMED' else 'checked_in',
                'phone': getattr(booking.customer, 'phone', None),
                'email': booking.customer.email,
            })

        # Get stops
        stops = HiaceRouteStop.objects.filter(route=route).order_by('stop_order')
        stops_data = []
        for stop in stops:
            stops_data.append({
                'name': stop.city.name,
                'time': (schedule.departure_datetime + stop.arrival_offset).strftime('%I:%M %p'),
                'type': 'boarding' if stop.is_boarding else 'dropping',
            })

        # Get earnings
        bookings = HiaceBooking.objects.filter(
            schedule=schedule,
            booking_status__in=['PAID', 'CONFIRMED']
        )
        total_earnings = bookings.aggregate(total=Sum('total_amount'))['total'] or 0
        platform_fee = float(total_earnings) * 0.10
        driver_earnings = float(total_earnings) - platform_fee

        # Get status
        now = timezone.now()
        if schedule.arrival_datetime < now:
            status = 'completed'
        elif schedule.departure_datetime <= now <= schedule.arrival_datetime:
            status = 'active'
        else:
            status = 'upcoming'

        # Get amenities
        amenities = []
        if hiace.wifi: amenities.append('WiFi')
        if hiace.charging: amenities.append('Charging')
        if hiace.ac: amenities.append('AC')

        return Response({
            'id': schedule.id,
            'route': f"{route.source_city.name} → {route.destination_city.name}",
            'from': route.source_city.name,
            'to': route.destination_city.name,
            'departureDate': schedule.departure_datetime.isoformat(),
            'departureTime': schedule.departure_datetime.isoformat(),
            'arrivalDate': schedule.arrival_datetime.isoformat(),
            'arrivalTime': schedule.arrival_datetime.isoformat(),
            'duration': self.format_duration(schedule.arrival_datetime - schedule.departure_datetime),
            'vehicle': hiace.hiace_name,
            'vehicleNumber': hiace.hiace_number,
            'vehicleType': hiace.hiace_type,
            'totalSeats': hiace.total_seats,
            'availableSeats': hiace.total_seats - booked_seats.count(),
            'bookedSeats': booked_seats.count(),
            'fare': schedule.fare if hasattr(schedule, 'fare') else None,
            'status': status,
            'driver': {
                'name': route.operator.fullName,
                'phone': getattr(route.operator, 'phone', 'N/A'),
                'rating': 4.8,
            },
            'passengers': passengers,
            'earnings': {
                'total': float(total_earnings),
                'platformFee': float(platform_fee),
                'driverEarnings': float(driver_earnings),
            },
            'amenities': amenities,
            'stops': stops_data,
        })

    def format_duration(self, duration):
        """Format duration to readable string"""
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        if hours > 0 and minutes > 0:
            return f"{hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h"
        else:
            return f"{minutes}m"

    def get_demo_trip_response(self, trip_id, user):
        """Return demo trip data for testing"""
        now = timezone.now()
        
        return Response({
            'id': int(trip_id),
            'route': 'Kathmandu → Pokhara',
            'from': 'Kathmandu',
            'to': 'Pokhara',
            'departureDate': (now + timedelta(hours=1)).isoformat(),
            'departureTime': (now + timedelta(hours=1)).isoformat(),
            'arrivalDate': (now + timedelta(hours=6, minutes=30)).isoformat(),
            'arrivalTime': (now + timedelta(hours=6, minutes=30)).isoformat(),
            'duration': '5h 30m',
            'vehicle': 'Sajha Bus',
            'vehicleNumber': 'BA 1 KA 1234',
            'vehicleType': 'AC',
            'totalSeats': 40,
            'availableSeats': 8,
            'bookedSeats': 32,
            'status': 'upcoming',
            'driver': {
                'name': user.fullName,
                'phone': getattr(user, 'phone', 'N/A'),
                'rating': 4.8,
            },
            'passengers': [
                {
                    'id': 1,
                    'name': 'Rahul Sharma',
                    'seatNumber': 'A1',
                    'bookingId': 'BK-12345',
                    'status': 'confirmed',
                    'phone': '+977 984-1234567',
                    'email': 'rahul@example.com',
                },
                {
                    'id': 2,
                    'name': 'Sita Giri',
                    'seatNumber': 'A2',
                    'bookingId': 'BK-12346',
                    'status': 'checked_in',
                    'phone': '+977 984-1234568',
                    'email': 'sita@example.com',
                }
            ],
            'earnings': {
                'total': 48000.0,
                'platformFee': 4800.0,
                'driverEarnings': 43200.0,
            },
            'amenities': ['WiFi', 'Charging', 'AC', 'TV'],
            'stops': [
                {'name': 'Kathmandu', 'time': '08:00 AM', 'type': 'boarding'},
                {'name': 'Naubise', 'time': '09:30 AM', 'type': 'boarding'},
                {'name': 'Pokhara', 'time': '01:30 PM', 'type': 'dropping'},
            ]
        })



class DriverTripDetailView(views.APIView):
    """
    Get detailed information about a specific trip for a driver
    Supports both Bus and Hiace schedules
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, trip_id):
        user = request.user
        
        # Debug logs
        print(f"=== DriverTripDetailView called ===")
        print(f"User: {user} (ID: {user.id})")
        print(f"Trip ID: {trip_id}")
        print(f"User Role: {user.role}")
        
        # Check if user is a driver/operator
        if user.role != 'D':
            return Response(
                {'error': 'Access denied. Only drivers can access this endpoint.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            trip = None
            trip_type = None
            
            # Get all buses and hiaces belonging to this driver
            user_buses = Bus.objects.filter(operator=user).values_list('id', flat=True)
            user_hiaces = Hiace.objects.filter(operator=user).values_list('id', flat=True)
            
            print(f"User buses: {list(user_buses)}")
            print(f"User hiaces: {list(user_hiaces)}")
            
            # Check bus schedules
            try:
                bus_schedule = Schedule.objects.select_related(
                    'route',
                    'route__source_city',
                    'route__destination_city',
                    'route__bus',
                    'route__operator'
                ).get(
                    id=trip_id,
                    route__bus__in=user_buses  # Only get schedules for user's buses
                )
                trip = bus_schedule
                trip_type = 'bus'
                print(f"Found bus schedule: {bus_schedule.id} - {bus_schedule.route}")
            except Schedule.DoesNotExist:
                print(f"No bus schedule found for trip {trip_id} belonging to user {user.id}")

            # If not found, check hiace schedules
            if not trip:
                try:
                    hiace_schedule = HiaceSchedule.objects.select_related(
                        'route',
                        'route__source_city',
                        'route__destination_city',
                        'route__hiace',
                        'route__operator'
                    ).get(
                        id=trip_id,
                        route__hiace__in=user_hiaces  # Only get schedules for user's hiaces
                    )
                    trip = hiace_schedule
                    trip_type = 'hiace'
                    print(f"Found hiace schedule: {hiace_schedule.id} - {hiace_schedule.route}")
                except HiaceSchedule.DoesNotExist:
                    print(f"No hiace schedule found for trip {trip_id} belonging to user {user.id}")
            
            if not trip:
                # Check if schedule exists but belongs to another operator
                bus_exists = Schedule.objects.filter(id=trip_id).exists()
                hiace_exists = HiaceSchedule.objects.filter(id=trip_id).exists()
                
                error_message = f'Trip with ID {trip_id} not found for this operator'
                
                if bus_exists or hiace_exists:
                    error_message = f'Trip with ID {trip_id} exists but belongs to another operator'
                
                return Response(
                    {'error': error_message},
                    status=status.HTTP_404_NOT_FOUND
                )

            print(f"Trip found! Type: {trip_type}")
            
            # Build response based on trip type
            if trip_type == 'bus':
                return self.build_bus_trip_response(trip, user)
            else:
                return self.build_hiace_trip_response(trip, user)

        except Exception as e:
            print(f"Error fetching trip details: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def build_bus_trip_response(self, schedule, user):
        route = schedule.route
        bus = route.bus
        
        # Get booked seats
        booked_seats = BookingSeat.objects.filter(
            booking__schedule=schedule,
            booking__booking_status__in=['PAID', 'CONFIRMED']
        )
        
        # Get passengers
        passengers = []
        for seat in booked_seats:
            booking = seat.booking
            passengers.append({
                'id': booking.id,
                'name': booking.customer.fullName,
                'seatNumber': seat.seat.seat_number,
                'bookingId': booking.booking_number,
                'status': 'confirmed' if booking.booking_status == 'CONFIRMED' else 'checked_in',
                'phone': getattr(booking.customer, 'phone', None),
                'email': booking.customer.email,
            })

        # Get stops
        stops = RouteStop.objects.filter(route=route).order_by('stop_order')
        stops_data = []
        for stop in stops:
            stops_data.append({
                'name': stop.city.name,
                'time': (schedule.departure_datetime + stop.arrival_offset).strftime('%I:%M %p'),
                'type': 'boarding' if stop.is_boarding else 'dropping',
            })

        # Get earnings
        bookings = Booking.objects.filter(
            schedule=schedule,
            booking_status__in=['PAID', 'CONFIRMED']
        )
        total_earnings = bookings.aggregate(total=Sum('total_amount'))['total'] or 0
        platform_fee = float(total_earnings) * 0.10
        driver_earnings = float(total_earnings) - platform_fee

        # Get status
        now = timezone.now()
        if schedule.arrival_datetime < now:
            status = 'completed'
        elif schedule.departure_datetime <= now <= schedule.arrival_datetime:
            status = 'active'
        else:
            status = 'upcoming'

        # Get amenities
        amenities = []
        if bus.wifi: amenities.append('WiFi')
        if bus.charging: amenities.append('Charging')
        if bus.ac: amenities.append('AC')
        if hasattr(bus, 'tv') and bus.tv: amenities.append('TV')

        return Response({
            'id': schedule.id,
            'route': f"{route.source_city.name} → {route.destination_city.name}",
            'from': route.source_city.name,
            'to': route.destination_city.name,
            'departureDate': schedule.departure_datetime.isoformat(),
            'departureTime': schedule.departure_datetime.isoformat(),
            'arrivalDate': schedule.arrival_datetime.isoformat(),
            'arrivalTime': schedule.arrival_datetime.isoformat(),
            'duration': self.format_duration(schedule.arrival_datetime - schedule.departure_datetime),
            'vehicle': bus.bus_name,
            'vehicleNumber': bus.bus_number,
            'vehicleType': bus.bus_type,
            'totalSeats': bus.total_seats,
            'availableSeats': bus.total_seats - booked_seats.count(),
            'bookedSeats': booked_seats.count(),
            'fare': schedule.fare if hasattr(schedule, 'fare') else None,
            'status': status,
            'driver': {
                'name': route.operator.fullName,
                'phone': getattr(route.operator, 'phone', 'N/A'),
                'rating': 4.8,
            },
            'passengers': passengers,
            'earnings': {
                'total': float(total_earnings),
                'platformFee': float(platform_fee),
                'driverEarnings': float(driver_earnings),
            },
            'amenities': amenities,
            'stops': stops_data,
        })

    def build_hiace_trip_response(self, schedule, user):
        route = schedule.route
        hiace = route.hiace
        
        # Get booked seats
        booked_seats = HiaceBookingSeat.objects.filter(
            booking__schedule=schedule,
            booking__booking_status__in=['PAID', 'CONFIRMED']
        )
        
        # Get passengers
        passengers = []
        for seat in booked_seats:
            booking = seat.booking
            passengers.append({
                'id': booking.id,
                'name': booking.customer.fullName,
                'seatNumber': seat.seat.seat_number,
                'bookingId': booking.booking_number,
                'status': 'confirmed' if booking.booking_status == 'CONFIRMED' else 'checked_in',
                'phone': getattr(booking.customer, 'phone', None),
                'email': booking.customer.email,
            })

        # Get stops
        stops = HiaceRouteStop.objects.filter(route=route).order_by('stop_order')
        stops_data = []
        for stop in stops:
            stops_data.append({
                'name': stop.city.name,
                'time': (schedule.departure_datetime + stop.arrival_offset).strftime('%I:%M %p'),
                'type': 'boarding' if stop.is_boarding else 'dropping',
            })

        # Get earnings
        bookings = HiaceBooking.objects.filter(
            schedule=schedule,
            booking_status__in=['PAID', 'CONFIRMED']
        )
        total_earnings = bookings.aggregate(total=Sum('total_amount'))['total'] or 0
        platform_fee = float(total_earnings) * 0.10
        driver_earnings = float(total_earnings) - platform_fee

        # Get status
        now = timezone.now()
        if schedule.arrival_datetime < now:
            status = 'completed'
        elif schedule.departure_datetime <= now <= schedule.arrival_datetime:
            status = 'active'
        else:
            status = 'upcoming'

        # Get amenities
        amenities = []
        if hiace.wifi: amenities.append('WiFi')
        if hiace.charging: amenities.append('Charging')
        if hiace.ac: amenities.append('AC')

        return Response({
            'id': schedule.id,
            'route': f"{route.source_city.name} → {route.destination_city.name}",
            'from': route.source_city.name,
            'to': route.destination_city.name,
            'departureDate': schedule.departure_datetime.isoformat(),
            'departureTime': schedule.departure_datetime.isoformat(),
            'arrivalDate': schedule.arrival_datetime.isoformat(),
            'arrivalTime': schedule.arrival_datetime.isoformat(),
            'duration': self.format_duration(schedule.arrival_datetime - schedule.departure_datetime),
            'vehicle': hiace.hiace_name,
            'vehicleNumber': hiace.hiace_number,
            'vehicleType': hiace.hiace_type,
            'totalSeats': hiace.total_seats,
            'availableSeats': hiace.total_seats - booked_seats.count(),
            'bookedSeats': booked_seats.count(),
            'fare': schedule.fare if hasattr(schedule, 'fare') else None,
            'status': status,
            'driver': {
                'name': route.operator.fullName,
                'phone': getattr(route.operator, 'phone', 'N/A'),
                'rating': 4.8,
            },
            'passengers': passengers,
            'earnings': {
                'total': float(total_earnings),
                'platformFee': float(platform_fee),
                'driverEarnings': float(driver_earnings),
            },
            'amenities': amenities,
            'stops': stops_data,
        })

    def format_duration(self, duration):
        """Format duration to readable string"""
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        if hours > 0 and minutes > 0:
            return f"{hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h"
        else:
            return f"{minutes}m"
        
class DriverVehiclesView(views.APIView):
  
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
   
        if user.role != 'D':
            return Response(
                {'error': 'Access denied. Only drivers can access this endpoint.'},
                status=status.HTTP_403_FORBIDDEN
            )


        for bus in Bus.objects.all():
            print(
                "Bus:", bus.id,
                "Operator:", bus.operator_id,
                "Name:", bus.bus_name,
            )

        try:
            vehicles = []

            # Get buses
            buses = Bus.objects.filter(operator=user)
            for bus in buses:
                # Get next trip
                next_schedule = Schedule.objects.filter(
                    route__bus=bus,
                    departure_datetime__gte=timezone.now(),
                    status='ACTIVE'
                ).order_by('departure_datetime').first()
                
                # Get available seats
                booked_seats = BookingSeat.objects.filter(
                    booking__schedule__route__bus=bus,
                    booking__booking_status='PAID'
                ).count()
                
                available_seats = bus.total_seats - booked_seats
                
                # Get trips completed
                trips_completed = Schedule.objects.filter(
                    route__bus=bus,
                    status='COMPLETED'
                ).count()
                
                # Get amenities
                amenities = []
                if bus.wifi: amenities.append('WiFi')
                if bus.charging: amenities.append('Charging')
                if bus.ac: amenities.append('AC')
                if hasattr(bus, 'tv') and bus.tv: amenities.append('TV')
                
                vehicles.append({
                    'id': bus.id,
                    'name': bus.bus_name,
                    'number': bus.bus_number,
                    'type': bus.bus_type,
                    'totalSeats': bus.total_seats,
                    'availableSeats': available_seats,
                    'status': 'active' if bus.status == 'ACTIVE' else 'inactive',
                    'amenities': amenities,
                    'rating': 4.5,  # Placeholder
                    'tripsCompleted': trips_completed,
                    'nextTrip': next_schedule.departure_datetime.strftime('%I:%M %p') if next_schedule else None,
                })

            # Get hiaces
            hiaces = Hiace.objects.filter(operator=user)
            for hiace in hiaces:
                # Get next trip
                next_schedule = HiaceSchedule.objects.filter(
                    route__hiace=hiace,
                    departure_datetime__gte=timezone.now(),
                    status='ACTIVE'
                ).order_by('departure_datetime').first()
                
                # Get available seats
                booked_seats = HiaceBookingSeat.objects.filter(
                    booking__schedule__route__hiace=hiace,
                    booking__booking_status='PAID'
                ).count()
                
                available_seats = hiace.total_seats - booked_seats
                
                # Get trips completed
                trips_completed = HiaceSchedule.objects.filter(
                    route__hiace=hiace,
                    status='COMPLETED'
                ).count()
                
                # Get amenities
                amenities = []
                if hiace.wifi: amenities.append('WiFi')
                if hiace.charging: amenities.append('Charging')
                if hiace.ac: amenities.append('AC')
                
                vehicles.append({
                    'id': hiace.id,
                    'name': hiace.hiace_name,
                    'number': hiace.hiace_number,
                    'type': hiace.hiace_type,
                    'totalSeats': hiace.total_seats,
                    'availableSeats': available_seats,
                    'status': 'active' if hiace.status == 'ACTIVE' else 'inactive',
                    'amenities': amenities,
                    'rating': 4.3,  # Placeholder
                    'tripsCompleted': trips_completed,
                    'nextTrip': next_schedule.departure_datetime.strftime('%I:%M %p') if next_schedule else None,
                })

            return Response(vehicles, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DriverProfileView(views.APIView): 
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        now = timezone.now()
        
        if user.role != 'D':
            return Response(
                {'error': 'Access denied. Only drivers can access this endpoint.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Get stats
            buses = Bus.objects.filter(operator=user)
            hiaces = Hiace.objects.filter(operator=user)
            
            # Total trips
            bus_trips = Schedule.objects.filter(
                route__bus__in=buses,
                arrival_datetime__lt=now,
                status="ACTIVE",
            ).count()
            
            hiace_trips = HiaceSchedule.objects.filter(route__hiace__in=hiaces,arrival_datetime__lt=now ,status='ACTIVE').count()
            total_trips = bus_trips + hiace_trips
            
            # Total earnings
            bus_result = Booking.objects.filter(
                schedule__route__bus__in=buses,
                booking_status="PAID",
            ).aggregate(
                total_amount=Sum("total_amount"),
                platform_amount=Sum("platform_amount"),
            )

            bus_earnings = (
                (bus_result["total_amount"] or 0)
                - (bus_result["platform_amount"] or 0)
            )

            # Hiace earnings
            hiace_result = HiaceBooking.objects.filter(
                schedule__route__hiace__in=hiaces,
                booking_status="PAID",
            ).aggregate(
                total_amount=Sum("total_amount"),
                platform_amount=Sum("platform_amount"),
            )

            hiace_earnings = (
                (hiace_result["total_amount"] or 0)
                - (hiace_result["platform_amount"] or 0)
            )
            
            total_earnings = float(bus_earnings) + float(hiace_earnings)
            
            # Get vehicle types
            vehicle_types = []
            for bus in buses:
                if bus.bus_type not in vehicle_types:
                    vehicle_types.append(bus.bus_type)
            for hiace in hiaces:
                if hiace.hiace_type not in vehicle_types:
                    vehicle_types.append(hiace.hiace_type)

            profile_data = {
                'id': user.id,
                'fullName': user.fullName,
                'email': user.email,
                'phone': getattr(user, 'phone', 'N/A'),
                'role': user.role,
                'profileImage': getattr(user, 'profile_image', None),
                'licenseNumber': getattr(user, 'license_number', None),
                'licenseExpiry': getattr(user, 'license_expiry', None),
                'experience': getattr(user, 'experience', 0),
                'rating': 4.6,  # Placeholder
                'totalTrips': total_trips,
                'totalEarnings': round(total_earnings, 2),
                'totalVehicle': len(buses) + len(hiaces),
                'joinDate': user.date_joined.isoformat() if hasattr(user, 'date_joined') else None,
                'vehicleType': vehicle_types,
                'languages': getattr(user, 'languages', ['Nepali', 'English']),
                'bio': getattr(user, 'bio', None),
                'address': getattr(user, 'address', None),
                'emergencyContact': {
                    'name': getattr(user, 'emergency_name', None),
                    'phone': getattr(user, 'emergency_phone', None),
                    'relationship': getattr(user, 'emergency_relationship', None),
                } if hasattr(user, 'emergency_name') else None,
            }

            return Response(profile_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request):
        user = request.user
        
        if user.role != 'D':
            return Response(
                {'error': 'Access denied. Only drivers can access this endpoint.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Update user fields
            fields = ['fullName', 'phone', 'address', 'bio', 'experience']
            for field in fields:
                if field in request.data:
                    setattr(user, field, request.data[field])
            
            user.save()
            
            return Response(
                {'message': 'Profile updated successfully'},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )